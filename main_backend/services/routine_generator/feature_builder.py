# app/services/routine_generator/feature_builder.py
"""
피쳐/유틸: 칼로리 추정, BMI 계산, 루틴 비율 계산
- 내부에서는 항상 영어 메타 정보(exercise_meta['category_1'])를 사용하도록 설계
"""

from typing import Dict, List, Any
from decimal import Decimal
from services.routine_generator.mappings import CATEGORY1_EN_TO_KO  # 필요시 사용

def _to_float(v):
    """Decimal / None 보호 변환"""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    try:
        return float(v)
    except Exception:
        return None

def calc_bmi(height_cm: float, weight_kg: float) -> float:
    """키(cm)와 몸무게(kg)으로 BMI 계산"""
    h = _to_float(height_cm)
    w = _to_float(weight_kg)
    if not h or h == 0:
        return 0.0
    return round(w / ((h/100.0) ** 2), 2)

def estimate_calories_for_exercise(met: float, weight_kg: float, duration_min: float) -> float:
    """간단한 MET 기반 칼로리 추정 (소수점)"""
    m = _to_float(met) or 3.0
    w = _to_float(weight_kg) or 70.0
    dur_h = (_to_float(duration_min) or 0.0) / 60.0
    # 계수 1.05: 활동 중 추가 인자(간단 보정)
    return (m * w * dur_h) * 1.05

def compute_routine_ratios(ex_items: List[Dict[str, Any]]) -> Dict[str, float]:
    """루틴 내 상/하/대사성 비율 계산 (ex_items에는 exercise_meta가 있어야 함)"""
    total_sets = sum(int(it.get('sets', 0)) for it in ex_items)
    if total_sets == 0:
        return {"upper_ratio": 0.0, "lower_ratio": 0.0, "metabolic_ratio": 0.0}
    upper = 0.0
    lower = 0.0
    metabolic = 0.0
    for item in ex_items:
        sets = int(item.get('sets', 0))
        ex_meta = item.get('exercise_meta') or {}
        cat1 = (ex_meta.get('category_1') or '').upper()
        ex_type = (ex_meta.get('type') or '').upper()
        if cat1 == 'UPPER_BODY':
            upper += sets
        elif cat1 == 'LOWER_BODY':
            lower += sets
        elif cat1 in ('FULL_BODY', 'CORE'):
            upper += 0.5 * sets
            lower += 0.5 * sets
        # '유산소' 문자열은 한국어가 섞일 가능성 있으므로 대소문자 체크 후 포함 검사
        if 'CARDIO' in ex_type or '유산소' in ex_type:
            metabolic += sets
    return {
        "upper_ratio": round(upper / total_sets, 4),
        "lower_ratio": round(lower / total_sets, 4),
        "metabolic_ratio": round(metabolic / total_sets, 4),
    }

