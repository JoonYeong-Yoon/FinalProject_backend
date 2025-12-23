# app/services/routine_generator/reps_predictor.py
"""
RepsPredictor 모듈 (개선판)
- 역할:
    각 운동(ex_meta)에 대해 '세트 수, 반복 수, 휴식(sec), 소요 시간(sec)' 을 예측하여 반환.
    모델이 학습 시 사용한 feature 스키마와 예측 시 입력 스키마가 다를 경우 자동 정렬/보정하여
    LightGBM의 "number of features" 형태 오류를 방지.

- 모델 파일:
    ai_models/reps_predictor_model.pkl  (sklearn-like 또는 LightGBM)
    ai_models/label_encoders.pkl        (선택적: 라벨 인코더 딕셔너리)

- 주요 함수/클래스:
    RepsPredictor.predict_for_exercise(user_info: dict, ex_meta: dict) -> dict
    predict_reps_for_exercise(user_info, ex_meta)  # 편의 함수 (싱글턴)

- 동작 정책:
    - 모델 로드 성공 시: 모델 입력 피처를 모델이 기대하는 순서/이름에 맞춰 정렬한 뒤 예측 시도.
    - 모델 출력이 다차원일 경우([set,reps,rest,duration]) 우선 사용.
    - 모델 출력이 1차원(예: 권장 반복수)일 경우 규칙적으로 나머지 값 구성.
    - 모델/인코더 없거나 예측 실패 시 규칙 기반 폴백 반환.
    - 한글/영어 명칭 상호변환을 위해 mappings를 사용(있으면).
"""
from __future__ import annotations
import os
import pickle
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# 기본 경로 (프로젝트 루트 기준)
DEFAULT_MODEL_PATH = "ai_models/reps_predictor_model.pkl"
DEFAULT_ENCODERS_PATH = "ai_models/label_encoders.pkl"

# optional mappings (한글 <-> 영어) - 서비스 구조에 따라 경로 조정
try:
    from services.routine_generator.mappings import map_ko_to_en, EXERCISE_KO_TO_EN, GOAL_KO_TO_EN
except Exception:
    try:
        # 개발/테스트 시 상대경로
        from services.routine_generator.mappings import map_ko_to_en, EXERCISE_KO_TO_EN, GOAL_KO_TO_EN
    except Exception:
        map_ko_to_en = None
        EXERCISE_KO_TO_EN = {}
        GOAL_KO_TO_EN = {}

# ---------- 유틸: 안전 변환 ----------
def _to_float_safe(v: Optional[object], default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        return float(v)
    except Exception:
        try:
            return float(str(v))
        except Exception:
            return default

def _to_int_safe(v: Optional[object], default: int = 0) -> int:
    if v is None:
        return default
    try:
        return int(round(float(v)))
    except Exception:
        try:
            return int(v)
        except Exception:
            return default

# ---------- RepsPredictor 클래스 ----------
class RepsPredictor:
    """
    모델 로드, 입력 피처 정렬, 예측, 폴백을 담당하는 래퍼 클래스.
    """

    def __init__(self,
                 model_path: str = DEFAULT_MODEL_PATH,
                 encoders_path: str = DEFAULT_ENCODERS_PATH):
        self.model_path = model_path
        self.encoders_path = encoders_path
        self.model = None
        self.encoders = None
        # 모델이 기대하는 feature 이름 목록 (학습 모델에서 읽어옴)
        self.expected_feature_names: Optional[List[str]] = None
        self._load_model_and_encoders()

    def _load_model_and_encoders(self) -> None:
        """
        모델과 라벨 인코더(있다면)를 로드.
        모델이 로드되면 가능한 경우 모델의 feature 이름을 추출하여
        예측 시 DataFrame 컬럼 정렬에 사용.
        """
        # 모델 로드
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "rb") as f:
                    self.model = pickle.load(f)
                logger.info(f"✅ RepsPredictor: 모델 로드됨 ({self.model_path})")
            except Exception as e:
                logger.warning(f"⚠️ RepsPredictor: 모델 로드 실패: {e}")
                self.model = None
        else:
            logger.warning(f"⚠️ RepsPredictor: 모델 파일 없음 ({self.model_path}), 규칙 기반 사용")
            self.model = None

        # 인코더 로드 (선택)
        if os.path.exists(self.encoders_path):
            try:
                with open(self.encoders_path, "rb") as f:
                    self.encoders = pickle.load(f)
                logger.info(f"✅ RepsPredictor: 라벨 인코더 로드됨 ({self.encoders_path})")
            except Exception as e:
                logger.warning(f"⚠️ RepsPredictor: 인코더 로드 실패: {e}")
                self.encoders = None
        else:
            self.encoders = None

        # 모델이 있으면 기대 feature 이름을 추출 시도
        if self.model is not None:
            try:
                self.expected_feature_names = self._get_model_feature_names(self.model)
                logger.info(f"🔎 모델 기대 feature: {self.expected_feature_names}")
            except Exception as e:
                logger.warning(f"⚠️ RepsPredictor: 모델의 feature 이름을 읽지 못함: {e}")
                self.expected_feature_names = None

    def _get_model_feature_names(self, model) -> Optional[List[str]]:
        """
        로드된 모델에서 학습 시 사용한 feature 이름을 추출.
        - LGBMRegressor (scikit-learn API): model.feature_name_
        - lightgbm.Booster: model.feature_name()
        - sklearn 모델: (feature names 정보가 없을 수 있음) -> None 반환
        """
        # sklearn LGBMRegressor 등
        try:
            # LGBMRegressor (sklearn API)
            if hasattr(model, "feature_name_") and getattr(model, "feature_name_") is not None:
                return list(model.feature_name_)
        except Exception:
            pass

        # LightGBM Booster
        try:
            # some wrappers may expose booster_
            booster = None
            if hasattr(model, "booster_") and model.booster_ is not None:
                booster = model.booster_
            elif hasattr(model, "booster") and callable(model.booster):
                booster = model.booster()
            elif hasattr(model, "feature_name") and callable(model.feature_name):
                # Booster-like
                return list(model.feature_name())
            if booster is not None and hasattr(booster, "feature_name"):
                return list(booster.feature_name())
        except Exception:
            pass

        # sklearn trees 등에서는 feature names가 없을 수 있음 -> None 반환
        return None

    def _prepare_features(self, user_info: Dict[str, Any], ex_meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        모델 입력용 피처 사전 생성.
        - user_info: age, gender, fitness_level, goal, bmi, weight_kg, body_fat, skeletal_muscle 등
        - ex_meta: id, name, category_1, difficulty, MET 등 (DB에서 온 항목)
        """
        # 안전한 타입 변환 및 기본값
        age = _to_int_safe(user_info.get("age"), 30)
        gender = user_info.get("gender") or user_info.get("sex") or "M"
        fitness_level = _to_int_safe(user_info.get("fitness_level"), 1)
        goal = user_info.get("goal") or "MAINTAIN"

        # 한글 goal이 들어왔을 경우 매핑 (있으면)
        try:
            if GOAL_KO_TO_EN and isinstance(goal, str) and goal in GOAL_KO_TO_EN:
                goal = GOAL_KO_TO_EN[goal]
        except Exception:
            pass

        # exercise name 한글 -> 영어 변환 (ex_meta may have Korean)
        ex_id = ex_meta.get("id")
        ex_name = ex_meta.get("name")
        try:
            if map_ko_to_en and isinstance(ex_name, str):
                mapped = map_ko_to_en(ex_name) if callable(map_ko_to_en) else None
                if mapped:
                    ex_name = mapped
        except Exception:
            # mapping 에러 무시
            pass

        feat = {
            "age": age,
            "gender": gender,
            "fitness_level": fitness_level,
            "goal": goal,
            "bmi": _to_float_safe(user_info.get("bmi"), 24.0),
            "weight_kg": _to_float_safe(user_info.get("weight_kg"), 70.0),
            "body_fat": _to_float_safe(user_info.get("body_fat"), 0.0),
            "skeletal_muscle": _to_float_safe(user_info.get("skeletal_muscle"), 0.0),
            "exercise_id": str(ex_id) if ex_id is not None else (str(ex_name) if ex_name is not None else "UNKNOWN"),
            "exercise_category": (ex_meta.get("category_1") or ex_meta.get("category") or "UNKNOWN"),
            "exercise_difficulty": _to_int_safe(ex_meta.get("difficulty"), 3),
            "exercise_MET": _to_float_safe(ex_meta.get("MET") or ex_meta.get("met"), 3.0),
        }

        # 라벨 인코더가 있으면 안전하게 변환(학습 당시 사용한 인코더를 따름)
        if self.encoders:
            for col in ("gender", "goal", "exercise_id", "exercise_category"):
                if col in self.encoders and feat.get(col) is not None:
                    le = self.encoders[col]
                    val = feat[col]
                    try:
                        classes = getattr(le, "classes_", None)
                        if classes is not None and val not in classes:
                            # unknown -> 첫 번째 클래스(안전 대체)
                            val = classes[0]
                        feat[col] = int(le.transform([val])[0])
                    except Exception:
                        # 변환 실패 시 원본 유지
                        feat[col] = feat[col]

        return feat

    def _align_dataframe_to_model(self, df):
        """
        모델이 기대하는 feature names(self.expected_feature_names)가 있으면,
        df의 컬럼을 그 순서에 맞춰 정렬/보정함.

        규칙:
            - 모델 기대 컬럼이 df에 없으면 0으로 추가 (numeric 기본값)
            - df에 불필요한 컬럼이 있으면 제거
            - 반환: 정렬된 DataFrame
        """
        if self.expected_feature_names is None:
            # 모델의 feature 정보가 없으면 원본 df 반환
            return df

        import pandas as pd
        expected = list(self.expected_feature_names)
        # ensure unique
        expected = list(dict.fromkeys(expected))

        # Add missing columns with default 0
        for col in expected:
            if col not in df.columns:
                df[col] = 0.0

        # Drop extra cols
        extra = [c for c in df.columns if c not in expected]
        if extra:
            logger.debug(f"RepsPredictor: 예측 입력에 불필요한 컬럼 제거: {extra}")
            df = df.drop(columns=extra)

        # Reorder to expected
        df = df[expected]
        return df

    def _model_predict(self, feature_df):
        """
        모델에 feature_df를 넣어 예측 시도.
        - feature_df는 pandas DataFrame으로 전달되어야 함.
        - 이 함수가 예측 실패시 None 반환.
        """
        if self.model is None:
            return None

        # 정렬/보정: 모델이 기대하는 컬럼 명이 있으면 정렬
        try:
            feature_df = self._align_dataframe_to_model(feature_df)
        except Exception as e:
            logger.warning(f"RepsPredictor: 입력 정렬 중 예외: {e}")

        try:
            preds = self.model.predict(feature_df)
            return preds
        except Exception as e:
            logger.warning(f"RepsPredictor: 첫 예측 시도 실패: {e}")
            try:
                # 일부 모델은 booster 호출 필요할 수도 있지만 이미 시도했으므로 None 반환
                preds = self.model.predict(feature_df)
                return preds
            except Exception as e2:
                logger.error(f"RepsPredictor: 모델 예측 불가: {e2}")
                return None

    def predict_for_exercise(self, user_info: Dict[str, Any], ex_meta: Dict[str, Any]) -> Dict[str, int]:
        """
        외부 호출용 메서드.
        반환값: {"set_count": int, "reps": int, "rest_sec": int, "duration_sec": int}
        """
        # 1) 피처 준비
        features = self._prepare_features(user_info, ex_meta)

        # 2) 모델이 없으면 규칙 기반 폴백
        if self.model is None:
            return self._fallback_rule_based(features, ex_meta)

        # 3) 모델 예측 시도
        try:
            import pandas as pd
            df = pd.DataFrame([features])

            # 예측
            preds = self._model_predict(df)
            if preds is None:
                raise RuntimeError("모델 예측 결과 없음")

            # preds가 2차원(예: [[set,reps,rest,duration], ...])이면 그 값을 사용
            first = preds[0]
            if hasattr(first, "__len__") and len(first) >= 4:
                set_count = _to_int_safe(first[0], 3)
                reps = _to_int_safe(first[1], 10)
                rest_sec = _to_int_safe(first[2], 60)
                duration_sec = _to_int_safe(first[3], max(10, reps * 3 * set_count))
                # 최소값 보정
                set_count = max(1, set_count)
                reps = max(1, reps)
                rest_sec = max(5, rest_sec)
                duration_sec = max(10, duration_sec)
                return {
                    "set_count": set_count,
                    "reps": reps,
                    "rest_sec": rest_sec,
                    "duration_sec": duration_sec
                }

            # preds가 1차원(예: [reps_pred, ...]) 혹은 스칼라 -> 권장 반복수 취급
            target_reps = None
            try:
                if hasattr(preds, "__len__") and len(preds) > 0:
                    target_reps = float(preds[0])
                else:
                    target_reps = float(preds)
            except Exception:
                target_reps = None

            if target_reps is not None:
                reps = max(3, int(round(target_reps)))
                # set_count: 난이도 기반 간단 결정
                diff = _to_int_safe(features.get("exercise_difficulty"), 3)
                set_count = 3 if diff <= 3 else 4
                rest_sec = 60 if diff <= 3 else 90
                duration_sec = max(10, int(reps * 3 * set_count))
                return {
                    "set_count": set_count,
                    "reps": reps,
                    "rest_sec": rest_sec,
                    "duration_sec": duration_sec
                }

            # 그 외 예측 실패 시 폴백
            return self._fallback_rule_based(features, ex_meta)

        except Exception as e:
            logger.error(f"RepsPredictor.predict_for_exercise 예외: {e}")
            return self._fallback_rule_based(features, ex_meta)

    def _fallback_rule_based(self, features: Dict[str, Any], ex_meta: Dict[str, Any]) -> Dict[str, int]:
        """
        규칙 기반 폴백:
        - 난이도(difficulty) 중심으로 set_count/ rest_sec 결정
        - goal에 따라 reps 대략 결정
        - duration: reps * 3초 * sets
        """
        diff = _to_int_safe(features.get("exercise_difficulty"), 3)
        base_sets = 3 if diff <= 3 else 4
        goal = features.get("goal", "MAINTAIN")
        goal_up = str(goal).upper()
        if goal_up in ("MUSCLE_GAIN", "근성장", "MUSCLE"):
            reps = 8 if diff >= 4 else 10
        elif goal_up in ("FAT_LOSS", "체지방감소", "FAT"):
            reps = 12
        elif goal_up in ("ENDURANCE", "지구력"):
            reps = 15
        else:
            reps = 10
        rest_sec = 60 if diff <= 3 else 90
        duration_sec = int(max(10, reps * 3 * base_sets))
        return {
            "set_count": base_sets,
            "reps": reps,
            "rest_sec": rest_sec,
            "duration_sec": duration_sec
        }

# ---------- 싱글턴 편의 함수 ----------
_default_predictor: Optional[RepsPredictor] = None

def predict_reps_for_exercise(user_info: Dict[str, Any], ex_meta: Dict[str, Any]) -> Dict[str, int]:
    """
    편의 호출 함수 (모듈 외부에서 간단 호출 가능).
    내부적으로 싱글턴 RepsPredictor 인스턴스 사용.
    """
    global _default_predictor
    if _default_predictor is None:
        _default_predictor = RepsPredictor()
    return _default_predictor.predict_for_exercise(user_info, ex_meta)




