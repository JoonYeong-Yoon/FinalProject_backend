# app/services/routine_generator/reps_predictor.py
"""
RepsPredictor 모듈
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

# optional mappings
try:
    from services.routine_generator.mappings import map_ko_to_en, EXERCISE_KO_TO_EN, GOAL_KO_TO_EN
except Exception:
    map_ko_to_en = None
    EXERCISE_KO_TO_EN = {}
    GOAL_KO_TO_EN = {}

# ---------- 경로 해석 ----------
def _resolve_models_path(filename: str) -> str:
    """
    1) AI_MODELS_DIR 환경변수(컨테이너) 우선
    2) 없으면 현재 파일 기준으로 프로젝트 루트 추정 후 ai_models/filename
    """
    env_dir = os.getenv("AI_MODELS_DIR")
    if env_dir:
        p = os.path.join(env_dir, filename)
        return os.path.normpath(p)

    # fallback: this file: .../services/routine_generator/reps_predictor.py
    here = os.path.abspath(os.path.dirname(__file__))
    # .../services/routine_generator -> .../ (app root)
    app_root = os.path.normpath(os.path.join(here, "..", ".."))
    p = os.path.join(app_root, "ai_models", filename)
    return os.path.normpath(p)

DEFAULT_MODEL_PATH = _resolve_models_path("reps_predictor_model.pkl")
DEFAULT_ENCODERS_PATH = _resolve_models_path("label_encoders.pkl")


# ---------- 규칙 기반 (요구사항 반영) ----------
def _is_plank_like(ex_meta: Dict[str, Any]) -> bool:
    name = (ex_meta.get("name") or "").lower()
    # 필요하면 더 추가
    return "plank" in name

def _rule_reps_and_duration(user_info: Dict[str, Any], ex_meta: Dict[str, Any]) -> Dict[str, int]:
    fl = _to_int_safe(user_info.get("fitness_level"), 1)
    fl = 1 if fl < 1 else (3 if fl > 3 else fl)

    # plank 계열은 기존 정책 유지
    if _is_plank_like(ex_meta):
        reps = 2 + fl          # 3 / 4 / 5 (분)
        duration_sec = reps * 60
        return {
            "reps": reps,
            "duration_sec": duration_sec
        }

    # 일반 운동 reps 정책
    if fl == 1:
        reps = 15
    elif fl == 2:
        reps = 30
    else:
        reps = 50

    # 세트당 수행 시간 (rep × 3초, 최소 30초)
    duration_sec = max(30, int(reps * 3))

    return {
        "reps": reps,
        "duration_sec": duration_sec
    }

def _rule_sets_and_rest(features: Dict[str, Any]) -> Dict[str, int]:
    diff = _to_int_safe(features.get("exercise_difficulty"), 3)
    # sets 최대 5 제한
    base_sets = 3 if diff <= 3 else 4
    base_sets = min(5, max(1, base_sets))
    rest_sec = 60 if diff <= 3 else 90
    rest_sec = max(30, rest_sec)
    return {"set_count": base_sets, "rest_sec": rest_sec}


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
        self.expected_feature_names: Optional[List[str]] = None
        self._load_model_and_encoders()

    def _load_model_and_encoders(self) -> None:
        logger.info(f"RepsPredictor paths -> model: {self.model_path} / encoders: {self.encoders_path}")

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

        # 기대 feature 이름 추출 시도
        if self.model is not None:
            try:
                self.expected_feature_names = self._get_model_feature_names(self.model)
                logger.info(f"🔎 모델 기대 feature: {self.expected_feature_names}")
            except Exception as e:
                logger.warning(f"⚠️ RepsPredictor: 모델 feature 이름 추출 실패: {e}")
                self.expected_feature_names = None

    def _get_model_feature_names(self, model) -> Optional[List[str]]:
        try:
            if hasattr(model, "feature_name_") and getattr(model, "feature_name_", None) is not None:
                return list(model.feature_name_)
        except Exception:
            pass

        try:
            booster = None
            if hasattr(model, "booster_") and model.booster_ is not None:
                booster = model.booster_
            elif hasattr(model, "booster") and callable(model.booster):
                booster = model.booster()
            elif hasattr(model, "feature_name") and callable(model.feature_name):
                return list(model.feature_name())
            if booster is not None and hasattr(booster, "feature_name"):
                return list(booster.feature_name())
        except Exception:
            pass

        return None

    def _prepare_features(self, user_info: Dict[str, Any], ex_meta: Dict[str, Any]) -> Dict[str, Any]:
        age = _to_int_safe(user_info.get("age"), 30)
        gender = user_info.get("gender") or user_info.get("sex") or "M"
        fitness_level = _to_int_safe(user_info.get("fitness_level"), 1)
        goal = user_info.get("goal") or "MAINTAIN"

        try:
            if GOAL_KO_TO_EN and isinstance(goal, str) and goal in GOAL_KO_TO_EN:
                goal = GOAL_KO_TO_EN[goal]
        except Exception:
            pass

        ex_id = ex_meta.get("id")
        ex_name = ex_meta.get("name")

        try:
            if map_ko_to_en and isinstance(ex_name, str):
                mapped = map_ko_to_en(ex_name) if callable(map_ko_to_en) else None
                if mapped:
                    ex_name = mapped
        except Exception:
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

        # 라벨 인코더 적용 (가능하면)
        if self.encoders:
            for col in ("gender", "goal", "exercise_id", "exercise_category"):
                if col in self.encoders and feat.get(col) is not None:
                    le = self.encoders[col]
                    val = feat[col]
                    try:
                        classes = getattr(le, "classes_", None)
                        if classes is not None and val not in classes:
                            val = classes[0]
                        feat[col] = int(le.transform([val])[0])
                    except Exception:
                        pass

        return feat

    def _align_dataframe_to_model(self, df):
        if self.expected_feature_names is None:
            return df

        expected = list(dict.fromkeys(list(self.expected_feature_names)))

        for col in expected:
            if col not in df.columns:
                df[col] = 0.0

        extra = [c for c in df.columns if c not in expected]
        if extra:
            df = df.drop(columns=extra)

        df = df[expected]
        return df

    def _model_predict(self, feature_df):
        if self.model is None:
            return None

        try:
            feature_df = self._align_dataframe_to_model(feature_df)
        except Exception as e:
            logger.warning(f"RepsPredictor: 입력 정렬 예외: {e}")

        try:
            return self.model.predict(feature_df)
        except Exception as e:
            logger.warning(f"RepsPredictor: 모델 예측 실패: {e}")
            return None

    def predict_for_exercise(self, user_info: Dict[str, Any], ex_meta: Dict[str, Any]) -> Dict[str, int]:
        """
        반환: {"set_count": int, "reps": int, "rest_sec": int, "duration_sec": int}
        - 모델이 있으면 모델 기반 예측을 우선 시도
        - 실패하거나 모델이 없으면 요구사항 기반 룰 폴백
        * reps: fitness_level 1/2/3 -> 10/12/15
        * plank류 reps: 3/4/5 (분 단위 느낌), duration: reps*60 (세트당)
        * sets 최대 5
        """
        # 1) feature 준비
        features = self._prepare_features(user_info, ex_meta)

        # 2) 룰 기반 기본값(요구사항)
        rr = _rule_reps_and_duration(user_info, ex_meta)
        # print("DEFAULT_MODEL_PATH",DEFAULT_MODEL_PATH)
        # print("DEFAULT_ENCODERS_PATH", DEFAULT_ENCODERS_PATH)
        sr = _rule_sets_and_rest(features)

        # 기본 룰 결과
        rule_out = {
            "set_count": sr["set_count"],
            "reps": rr["reps"],
            "rest_sec": sr["rest_sec"],
            "duration_sec": rr["duration_sec"],
        }

        # 3) 모델 없으면 룰 반환
        if self.model is None:
            return rule_out

        # 4) 모델 예측 시도
        try:
            import pandas as pd

            df = pd.DataFrame([features])
            preds = self._model_predict(df)
            if preds is None:
                return rule_out

            first = preds[0]

            # (A) 멀티아웃풋: [set, reps, rest, duration]
            if hasattr(first, "__len__") and len(first) >= 4:
                set_count = min(5, max(1, _to_int_safe(first[0], rule_out["set_count"])))
                reps = max(1, _to_int_safe(first[1], rule_out["reps"]))
                rest_sec = max(30, _to_int_safe(first[2], rule_out["rest_sec"]))
                duration_sec = max(10, _to_int_safe(first[3], rule_out["duration_sec"]))

                # print("check",first, rule_out["reps"], _to_int_safe(first[1], rule_out["reps"]))
                return {
                    "set_count": set_count,
                    "reps": reps,
                    "rest_sec": rest_sec,
                    "duration_sec": duration_sec,
                }

            # (B) 스칼라/1차원: reps만 예측한다고 가정
            try:
                pred_reps = float(first)
                # print("first",first, pred_reps)
                reps = max(1, int(round(pred_reps)))
            except Exception:
                return rule_out

            # reps만 모델이 주는 경우: sets/rest/duration은 요구사항 룰로
            return {
                "set_count": rule_out["set_count"],
                "reps": reps,
                "rest_sec": rule_out["rest_sec"],
                "duration_sec": rule_out["duration_sec"],
            }

        except Exception as e:
            logger.warning(f"RepsPredictor.predict_for_exercise 예측 실패 -> rule fallback: {e}")
            return rule_out

# ---------- 싱글턴 ----------
_default_predictor: Optional[RepsPredictor] = None

def predict_reps_for_exercise(user_info: Dict[str, Any], ex_meta: Dict[str, Any]) -> Dict[str, int]:
    global _default_predictor
    if _default_predictor is None:
        _default_predictor = RepsPredictor()
        _default_predictor.model = None # 모델 수정 후 삭제 필요
    return _default_predictor.predict_for_exercise(user_info, ex_meta)
