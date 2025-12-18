# app/services/routine_generator/scorer.py
"""
RoutineScorer 모듈 (개선판)
- 역할:
    생성된 루틴의 요약(summary: total_sets, ratios 등)을 입력받아
    LightGBM 기반 '루틴 점수(0~100)' 를 예측한다.
    → feature mismatch(예: LightGBM "number of features" 오류)를 자동 해결하도록
      입력 DataFrame을 모델이 학습 시 사용한 feature 스키마에 맞춰 정렬/보정.

- 모델 파일:
    ai_models/routine_scorer_lgbm.pkl
    ai_models/label_encoders.pkl (optional)

- 주요 기능:
    RoutineScorer.score(user_info, summary) -> float
    score_routine(user_info, summary)  # 싱글턴 래퍼

- 동작 정책:
    - 모델 로드 성공 시: 모델이 기대하는 feature 순서/이름에 맞게 DF를 정렬 후 예측.
    - feature 부족 → 0으로 채움 / feature 추가 → 삭제.
    - 예측 실패 또는 모델 없음 → 규칙 기반 점수 계산 fallback.
"""

import os
import pickle
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

DEFAULT_MODEL_PATH = "app/ai_models/routine_scorer_model.pkl"
DEFAULT_ENCODERS_PATH = "app/ai_models/routine_scorer_encoders.pkl"

# goal 한글→영어 변환 지원
try:
    from services.routine_generator.mappings import GOAL_KO_TO_EN
except Exception:
    try:
        from services.routine_generator.mappings import GOAL_KO_TO_EN
    except Exception:
        GOAL_KO_TO_EN = {}

# ---------- 유틸: 안전 숫자 변환 ----------
def _to_float_safe(v, default=0.0):
    if v is None:
        return default
    try:
        return float(v)
    except Exception:
        try:
            return float(str(v))
        except Exception:
            return default

def _to_int_safe(v, default=0):
    if v is None:
        return default
    try:
        return int(round(float(v)))
    except Exception:
        try:
            return int(v)
        except Exception:
            return default

# ============================================================
#                    RoutineScorer 클래스
# ============================================================
class RoutineScorer:
    """
    Routine 점수 산정기
    - 모델이 있으면 모델 예측
    - 모델 없음 또는 예측 실패 시 규칙 기반 fallback
    - LightGBM feature mismatch 자동 보정 기능 포함
    """

    def __init__(self,
                 model_path: str = DEFAULT_MODEL_PATH,
                 encoders_path: str = DEFAULT_ENCODERS_PATH):
        self.model_path = model_path
        self.encoders_path = encoders_path
        self.model = None
        self.encoders = None
        self.expected_feature_names: Optional[List[str]] = None
        self._load()

    # ---------------------------------------------------------
    #                  모델 / 인코더 로드
    # ---------------------------------------------------------
    def _load(self):
        # Load model
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "rb") as f:
                    self.model = pickle.load(f)
                logger.info(f"✅ RoutineScorer: 모델 로드됨 ({self.model_path})")
            except Exception as e:
                logger.warning(f"⚠️ RoutineScorer: 모델 로드 실패: {e}")
                self.model = None
        else:
            logger.warning(f"⚠️ RoutineScorer: 모델 없음 ({self.model_path})")
            self.model = None

        # Load encoders
        if os.path.exists(self.encoders_path):
            try:
                with open(self.encoders_path, "rb") as f:
                    self.encoders = pickle.load(f)
                logger.info(f"✅ RoutineScorer: 인코더 로드됨 ({self.encoders_path})")
            except Exception as e:
                logger.warning(f"⚠️ RoutineScorer: 인코더 로드 실패: {e}")
                self.encoders = None
        else:
            self.encoders = None

        # Extract feature names from model if possible
        if self.model is not None:
            try:
                self.expected_feature_names = self._get_model_feature_names(self.model)
                logger.info(f"🔎 RoutineScorer 모델 기대 feature: {self.expected_feature_names}")
            except Exception as e:
                logger.warning(f"⚠️ RoutineScorer: 모델 feature 정보 읽기 실패: {e}")
                self.expected_feature_names = None

    # ---------------------------------------------------------
    #          모델이 사용한 feature 이름 목록 추출
    # ---------------------------------------------------------
    def _get_model_feature_names(self, model) -> Optional[List[str]]:
        # LGBMRegressor (sklearn API)
        try:
            if hasattr(model, "feature_name_") and model.feature_name_:
                return list(model.feature_name_)
        except Exception:
            pass

        # LightGBM Booster
        try:
            booster = None
            if hasattr(model, "booster_"):
                booster = model.booster_
            elif hasattr(model, "booster") and callable(model.booster):
                booster = model.booster()

            if booster and hasattr(booster, "feature_name"):
                return list(booster.feature_name())
        except Exception:
            pass

        return None  # 모델에서 feature 이름을 구할 수 없을 때

    # ---------------------------------------------------------
    #           예측 전 DataFrame feature 정렬/보정
    # ---------------------------------------------------------
    def _align_dataframe(self, df):
        """
        모델이 기대하는 feature names(self.expected_feature_names)에 맞춰
        입력 DataFrame의 컬럼을 자동 정렬.
        - 누락된 컬럼 → 0으로 추가
        - 초과 컬럼 → 제거
        """
        if self.expected_feature_names is None:
            return df

        import pandas as pd

        expected = list(dict.fromkeys(self.expected_feature_names))  # unique 유지

        # Add missing features with default 0
        for col in expected:
            if col not in df.columns:
                df[col] = 0.0

        # Remove extra columns
        extra_cols = [c for c in df.columns if c not in expected]
        if extra_cols:
            logger.debug(f"RoutineScorer: 예측 입력 불필요 컬럼 제거: {extra_cols}")
            df = df.drop(columns=extra_cols)

        # Reorder
        df = df[expected]
        return df

    # ---------------------------------------------------------
    #            모델 입력용 feature 만들기
    # ---------------------------------------------------------
    def _prepare_features(self, user_info: Dict[str, Any], summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        summary: builder에서 제공한 루틴 요약
        user_info: goal, fitness_level, bmi 등
        """
        feat = {
            "time_available_minutes": _to_int_safe(summary.get("time_available_minutes"), 30),
            "total_sets": _to_int_safe(summary.get("total_sets"), 10),
            "total_exercises": _to_int_safe(summary.get("total_exercises"), 3),
            "metabolic_ratio": _to_float_safe(summary.get("metabolic_ratio"), 0.2),
            "upper_ratio": _to_float_safe(summary.get("upper_ratio"), 0.4),
            "lower_ratio": _to_float_safe(summary.get("lower_ratio"), 0.4),
            "user_goal": user_info.get("goal", "MAINTAIN"),
            "user_fitness_level": _to_int_safe(user_info.get("fitness_level"), 1),
            "user_bmi": _to_float_safe(user_info.get("bmi"), 24.0),
        }

        # 한글 goal → 영어 매핑
        try:
            if isinstance(feat["user_goal"], str) and feat["user_goal"] in GOAL_KO_TO_EN:
                feat["user_goal"] = GOAL_KO_TO_EN[feat["user_goal"]]
        except Exception:
            pass

        # goal 인코딩
        if self.encoders and "goal" in self.encoders:
            try:
                le = self.encoders["goal"]
                val = feat["user_goal"]
                classes = getattr(le, "classes_", [])
                if val not in classes:
                    val = classes[0]  # unknown → 첫 번째 클래스로 대체
                feat["user_goal"] = int(le.transform([val])[0])
            except Exception as e:
                logger.warning(f"RoutineScorer: goal 인코딩 실패: {e}")
                # fallback numeric mapping
                mapping = {
                    "MUSCLE_GAIN": 2, "FAT_LOSS": 1,
                    "ENDURANCE": 3, "MAINTAIN": 0
                }
                feat["user_goal"] = mapping.get(str(feat["user_goal"]).upper(), 0)
        else:
            # fallback numeric mapping
            mapping = {
                "MUSCLE_GAIN": 2, "FAT_LOSS": 1,
                "ENDURANCE": 3, "MAINTAIN": 0
            }
            feat["user_goal"] = mapping.get(str(feat["user_goal"]).upper(), 0)

        return feat

    # ---------------------------------------------------------
    #                     점수 계산
    # ---------------------------------------------------------
    def score(self, user_info: Dict[str, Any], summary: Dict[str, Any]) -> float:
        """
        반환: 0~100 사이 점수 (0~99.9로 클리핑)
        """
        features = self._prepare_features(user_info, summary)

        # 모델 없으면 fallback
        if self.model is None:
            return self._fallback_score(features)

        # 모델 예측
        try:
            import pandas as pd
            df = pd.DataFrame([features])

            # feature 정렬
            df = self._align_dataframe(df)

            pred = self.model.predict(df)[0]
            score = float(pred)
            return round(max(0.0, min(99.0, score)), 1)

        except Exception as e:
            logger.error(f"RoutineScorer.score 예측 실패: {e}")
            return self._fallback_score(features)

    # ---------------------------------------------------------
    #                  규칙 기반 점수 산정
    # ---------------------------------------------------------
    def _fallback_score(self, feat: Dict[str, Any]) -> float:
        score = 50.0
        score += feat["metabolic_ratio"] * 30.0
        score += (feat["total_sets"] - 8) * 1.2
        score += (feat["user_bmi"] - 22) * (-0.2)
        return round(max(0.0, min(99.0, score)), 1)


# ============================================================
#               싱글턴 래퍼 함수
# ============================================================

_default_scorer: Optional[RoutineScorer] = None

def score_routine(user_info: Dict[str, Any], summary: Dict[str, Any]) -> float:
    global _default_scorer
    if _default_scorer is None:
        _default_scorer = RoutineScorer()
    return _default_scorer.score(user_info, summary)
