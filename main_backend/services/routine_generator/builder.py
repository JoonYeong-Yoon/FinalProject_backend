# app/services/routine_generator/builder.py
"""
루틴 빌더 (3가지 전략)
- generate_three_strategy_routines(user_info, catalog, time_min)
  : 반환값은 리스트(3개) 각 요소는 {strategy, exercises, total_time_min, total_calories, score}
전략 종류:
  - time_based: 시간 내 최대 효율/운동소모를 목표로 (짧은 시간엔 고MET 위주)
  - efficiency_based: routine_scorer 모델 점수를 최대화 (모델 기반)
  - balance_based: 상/하/코어 균형을 맞추는 구성

주의:
- 입력 catalog는 영어 기반(ex['name']는 영어 key)이어야 함.
- router에서 이미 한국어->영어 변환을 수행했어야 함. 방어적으로 normalize 수행.
"""

from typing import List, Dict, Any
import random
from .feature_builder import estimate_calories_for_exercise, compute_routine_ratios
from .reps_predictor import predict_reps_for_exercise
from .scorer import score_routine
from services.routine_generator.mappings import (
    EXERCISE_KO_TO_EN, EXERCISE_EN_TO_KO, GOAL_KO_TO_EN, GOAL_EN_TO_KO,
    INJURY_KO_TO_EN, INJURY_EN_TO_KO, CANCEL_KO_TO_EN, CANCEL_EN_TO_KO,
    STATUS_KO_TO_EN, STATUS_EN_TO_KO, 
    CATEGORY1_KO_TO_EN, CATEGORY1_EN_TO_KO,
    map_ko_to_en, map_en_to_ko)

ALLOWED_EXERCISES_EN = set(EXERCISE_EN_TO_KO.keys())  # 17개 영어 key

def _to_float(v):
    from decimal import Decimal
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    try:
        return float(v)
    except:
        return None

def normalize_catalog(catalog: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """카탈로그 항목이 한국어 이름을 갖고 있으면 영어로 변환"""
    out = []
    for c in catalog:
        c = dict(c)  # 복사
        # name이 한국어라면 변환 (방어)
        if c.get('name') in EXERCISE_KO_TO_EN:
            c['name'] = EXERCISE_KO_TO_EN[c['name']]
        # id, difficulty, MET 등 타입 정리
        c['difficulty'] = int(c.get('difficulty') or 3)
        c['MET'] = _to_float(c.get('MET') or c.get('met') or 3.0)
        # ensure category_1 is EN
        cat1 = c.get('category_1')
        if cat1:
            c['category_1'] = (cat1 or '').upper()
        out.append(c)
    # 필터: 허용된 운동 목록(프로젝트 17종)
    out = [c for c in out if c['name'] in ALLOWED_EXERCISES_EN]
    return out

def build_routine_from_exercises(user_info: dict, exercises: List[Dict[str, Any]], time_min: int):
    """
    exercises: 이미 선택된 리스트 (각 ex는 영어 기반)
    반환: routine dict (exercises with set/reps/etc + totals + score)
    """
    ex_items = []
    total_cal = 0.0
    for ex in exercises:
        ex = dict(ex)
        # 예측기 호출 (세트/반복/시간/휴식)
        pred = predict_reps_for_exercise(user_info, ex)
        sets = int(pred.get("set_count", 3))
        reps = int(pred.get("reps", 10))
        rest_sec = int(pred.get("rest_sec", 60))
        duration_sec = int(pred.get("duration_sec") or max(10, int(reps * 2.5 * sets)))
        est_cal = estimate_calories_for_exercise(float(ex.get("MET") or 3.0), user_info.get("weight_kg", 70.0), duration_sec/60.0)
        item = {
            "exercise_id": ex.get("id"),
            "name": ex.get("name"),  # 영어 key
            "sets": sets,
            "reps": reps,
            "rest_sec": rest_sec,
            "duration_sec": duration_sec,
            "exercise_meta": ex,
            "est_calories": round(est_cal, 1)
        }
        ex_items.append(item)
        total_cal += est_cal

    ratios = compute_routine_ratios(ex_items)
    estimated_seconds = sum(it["duration_sec"] + it["rest_sec"] * it["sets"] for it in ex_items)
    estimated_minutes = round(estimated_seconds / 60.0, 1)

    # 시간 초과 시 세트 축소(간단 폴백)
    if estimated_minutes > time_min:
        for it in ex_items:
            while estimated_minutes > time_min and it["sets"] > 1:
                it["sets"] -= 1
                it["duration_sec"] = max(10, int(it["duration_sec"] * 0.8))
                estimated_seconds = sum(i["duration_sec"] + i["rest_sec"] * i["sets"] for i in ex_items)
                estimated_minutes = round(estimated_seconds / 60.0, 1)

    summary = {
        "time_available_minutes": time_min,
        "total_sets": sum(it["sets"] for it in ex_items),
        "total_exercises": len(ex_items),
        "metabolic_ratio": ratios["metabolic_ratio"],
        "upper_ratio": ratios["upper_ratio"],
        "lower_ratio": ratios["lower_ratio"],
    }
    score = score_routine(user_info, summary)
    return {
        "exercises": ex_items,
        "total_time_min": estimated_minutes,
        "total_calories": round(total_cal, 1),
        "score": score,
        "summary": summary
    }

def generate_three_strategy_routines(user_info: dict, catalog: List[Dict[str, Any]], time_min: int):
    """
    세 전략으로 각각 루틴을 생성하여 리스트로 반환
    strategies: time_based, efficiency_based, balance_based
    """
    catalog = normalize_catalog(catalog)
    if not catalog:
        return []

    # 난이도 필터
    fl = int(user_info.get("fitness_level") or 1)
    max_diff = 3 if fl == 1 else (4 if fl == 2 else 5)
    catalog = [c for c in catalog if (c.get("difficulty") or 3) <= max_diff]

    # 1) 시간 기반 (MET 우대)
    def time_score(ex):
        return float(ex.get("MET") or 1.0) - 0.1 * (ex.get("difficulty") or 3)
    n_ex = 3 if time_min <= 20 else (4 if time_min <= 35 else 5)
    time_sorted = sorted(catalog, key=time_score, reverse=True)
    time_selected = time_sorted[:n_ex]
    time_routine = build_routine_from_exercises(user_info, time_selected, time_min)
    time_routine["strategy"] = "time_based"

    # 2) 효율 기반 (샘플링 + scorer 최대화)
    sampled_candidates = []
    random.seed(hash(user_info.get("user_id") or "seed"))
    for _ in range(40):
        k = min(n_ex, max(3, len(catalog)))
        try:
            candidate = random.sample(catalog, k=k)
        except ValueError:
            candidate = catalog[:k]
        res = build_routine_from_exercises(user_info, candidate, time_min)
        sampled_candidates.append(res)
    efficiency_routine = max(sampled_candidates, key=lambda x: x["score"])
    efficiency_routine["strategy"] = "efficiency_based"

    # 3) 균형 기반 (상/하/코어 포함 보장)
    upper_candidates = [c for c in catalog if (c.get("category_1") or '').upper() == "UPPER_BODY"]
    lower_candidates = [c for c in catalog if (c.get("category_1") or '').upper() == "LOWER_BODY"]
    core_candidates = [c for c in catalog if (c.get("category_1") or '').upper() in ("CORE", "FULL_BODY")]

    chosen = []
    if upper_candidates:
        chosen.append(random.choice(upper_candidates))
    if lower_candidates:
        chosen.append(random.choice(lower_candidates))
    if core_candidates:
        chosen.append(random.choice(core_candidates))

    remaining = [c for c in catalog if c not in chosen]
    idx = 0
    while len(chosen) < n_ex and idx < len(remaining):
        chosen.append(remaining[idx])
        idx += 1

    balance_routine = build_routine_from_exercises(user_info, chosen, time_min)
    balance_routine["strategy"] = "balance_based"

    routines = [time_routine, efficiency_routine, balance_routine]
    routines_sorted = sorted(routines, key=lambda x: x["score"], reverse=True)
    return routines_sorted

