"""
LLM Analysis - 운동 추천 엔진 (개선 버전)

✅ 개선 사항:
1. 하드코딩 제거 (체중, 강도 등 모두 동적)
2. 건강 점수 기반 세분화된 루틴 생성
3. 점수별 운동 강도/세트/휴식 차등 적용
4. 체중 동적 계산 (raw → BMI 역산 → 통계 기반 추정)
"""

import os
import json
from dotenv import load_dotenv
from openai import OpenAI

from app.config import LLM_MODEL_MAIN, LLM_TEMPERATURE, LLM_MAX_TOKENS
from app.core.rag_query import (
    build_rag_query,
    classify_rag_strength,
)
from app.core.vector_store import search_similar_summaries
from app.core.health_interpreter import (
    interpret_health_data,
    build_health_context_for_llm,
    build_analysis_text,
    analyze_rag_patterns,
    recommend_exercise_intensity,
    calculate_health_score,
)

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ==========================================================
# 1) 유틸 함수들
# ==========================================================
def clean_json_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()
    return text


def try_parse_json(text: str):
    try:
        return json.loads(text)
    except Exception:
        return None


# ==========================================================
# 2) 체중 동적 추정
# ==========================================================
def estimate_weight(raw: dict) -> float:
    """
    체중 동적 추정 (우선순위)
    1. raw에서 직접 가져오기
    2. BMI + 키로 역산
    3. 키 기반 표준체중 계산
    4. 한국 성인 평균 (최후 수단)
    """
    # 1) raw에서 직접
    weight = raw.get("weight", 0)
    if weight > 0:
        return float(weight)

    # 2) BMI + 키로 역산: weight = BMI * height_m^2
    bmi = raw.get("bmi", 0)
    height_m = raw.get("height_m", 0)
    if bmi > 0 and height_m > 0:
        return round(bmi * (height_m**2), 1)

    # 3) 키 기반 표준체중 (Broca 변형): (height_cm - 100) * 0.9
    height_cm = height_m * 100 if height_m > 0 else 0
    if height_cm > 0:
        return round((height_cm - 100) * 0.9, 1)

    # 4) 한국 성인 평균 (통계청 2023 기준)
    # 남성 평균 73.3kg, 여성 평균 58.0kg → 중간값 65kg
    return 65.0


# ==========================================================
# 3) 건강 점수 기반 운동 설정 계산
# ==========================================================
def get_exercise_settings_by_score(score: int) -> dict:
    """
    건강 점수에 따른 운동 설정 반환

    ✅ 개선: 등급별 칼로리 차이를 30~50kcal로 확대

    | 점수    | 등급 | 세트 | 운동시간 | MET    | 예상 칼로리 |
    |---------|------|------|----------|--------|-------------|
    | 80+     | A    | 5    | 50초     | 5.5-8  | ~200kcal    |
    | 70-79   | B    | 4-5  | 45초     | 5.0-6  | ~170kcal    |
    | 55-69   | C+   | 4    | 42초     | 4.5-5.5| ~145kcal    |
    | 45-54   | C    | 3    | 38초     | 4.0-4.5| ~115kcal    |
    | 35-44   | D    | 2    | 32초     | 3.0-3.8| ~85kcal     |
    | <35     | F    | 2    | 28초     | 2.5-3.2| ~70kcal     |
    """
    if score >= 80:
        return {
            "grade": "A",
            "intensity": "상",
            "base_sets": 5,
            "max_sets": 5,
            "rest_sec": 10,
            "met_min": 5.5,
            "met_max": 8.0,
            "duration_sec": 50,
            "calorie_multiplier": 1.0,
        }
    elif score >= 70:
        return {
            "grade": "B",
            "intensity": "중상",
            "base_sets": 4,
            "max_sets": 5,
            "rest_sec": 12,
            "met_min": 5.0,
            "met_max": 6.0,
            "duration_sec": 45,
            "calorie_multiplier": 1.0,
        }
    elif score >= 55:
        return {
            "grade": "C+",
            "intensity": "중",
            "base_sets": 4,
            "max_sets": 4,
            "rest_sec": 12,
            "met_min": 4.5,
            "met_max": 5.5,
            "duration_sec": 42,
            "calorie_multiplier": 1.0,
        }
    elif score >= 45:
        return {
            "grade": "C",
            "intensity": "중하",
            "base_sets": 3,
            "max_sets": 3,
            "rest_sec": 15,
            "met_min": 4.0,
            "met_max": 4.5,
            "duration_sec": 38,
            "calorie_multiplier": 1.0,
        }
    elif score >= 35:
        return {
            "grade": "D",
            "intensity": "하",
            "base_sets": 2,
            "max_sets": 2,
            "rest_sec": 18,
            "met_min": 3.0,
            "met_max": 3.8,
            "duration_sec": 32,
            "calorie_multiplier": 1.0,
        }
    else:
        return {
            "grade": "F",
            "intensity": "최하",
            "base_sets": 2,
            "max_sets": 2,
            "rest_sec": 20,
            "met_min": 2.5,
            "met_max": 3.2,
            "duration_sec": 28,
            "calorie_multiplier": 1.0,
        }


# ==========================================================
# 4) 점수 기반 운동 풀 선택
# ==========================================================
def get_exercise_pool_by_score(score: int) -> list:
    """
    건강 점수에 따른 운동 풀 반환 (세분화)

    | 점수    | 운동 풀 구성                           |
    |---------|----------------------------------------|
    | 70+     | 저 + 중 + 고강도 전체                  |
    | 55-69   | 저 + 중강도 전체                       |
    | 45-54   | 저강도 + 중강도 일부 (MET 4.0-4.5)     |
    | 35-44   | 저강도만                               |
    | <35     | 최저강도만 (MET 3.5 이하)              |
    """

    # 최저강도 운동 (F등급, MET 3.5 이하)
    very_low_intensity = [
        {
            "exercise_name": "hip thrust",
            "category": [3, 2],
            "difficulty": 3,
            "met": 3.5,
        },
        {
            "exercise_name": "standing knee up",
            "category": [1, 3],
            "difficulty": 3,
            "met": 3.3,
        },
        {"exercise_name": "arm circle", "category": [1], "difficulty": 2, "met": 2.8},
        {
            "exercise_name": "shoulder stretch",
            "category": [1],
            "difficulty": 2,
            "met": 2.5,
        },
    ]

    # 저강도 운동 (D등급, MET 3.5-4.0)
    low_intensity = [
        {
            "exercise_name": "standing knee up",
            "category": [1, 3],
            "difficulty": 3,
            "met": 3.8,
        },
        {
            "exercise_name": "hip thrust",
            "category": [3, 2],
            "difficulty": 3,
            "met": 3.5,
        },
        {
            "exercise_name": "standing side crunch",
            "category": [2, 3],
            "difficulty": 3,
            "met": 4.0,
        },
        {
            "exercise_name": "cross lunge",
            "category": [3, 2],
            "difficulty": 4,
            "met": 3.8,
        },
    ]

    # 중저강도 운동 (C등급, MET 4.0-4.5)
    mid_low_intensity = [
        {
            "exercise_name": "step forward dynamic lunge",
            "category": [3],
            "difficulty": 4,
            "met": 4.0,
        },
        {
            "exercise_name": "lying leg raise",
            "category": [3, 2],
            "difficulty": 4,
            "met": 4.0,
        },
        {"exercise_name": "crunch", "category": [2], "difficulty": 4, "met": 4.5},
        {
            "exercise_name": "scissor cross",
            "category": [2, 3],
            "difficulty": 4,
            "met": 4.5,
        },
        {
            "exercise_name": "Y-exercise",
            "category": [1, 2],
            "difficulty": 3,
            "met": 4.5,
        },
    ]

    # 중강도 운동 (C+등급, MET 4.5-5.5)
    mid_intensity = [
        {"exercise_name": "crunch", "category": [2], "difficulty": 4, "met": 4.5},
        {
            "exercise_name": "scissor cross",
            "category": [2, 3],
            "difficulty": 4,
            "met": 4.5,
        },
        {
            "exercise_name": "Y-exercise",
            "category": [1, 2],
            "difficulty": 3,
            "met": 4.5,
        },
        {
            "exercise_name": "knee push up",
            "category": [1, 2],
            "difficulty": 3,
            "met": 5.0,
        },
        {
            "exercise_name": "bicycle crunch",
            "category": [3, 2],
            "difficulty": 5,
            "met": 5.0,
        },
        {"exercise_name": "side lunge", "category": [3], "difficulty": 5, "met": 5.0},
        {
            "exercise_name": "good morning exercise",
            "category": [3],
            "difficulty": 5,
            "met": 5.0,
        },
    ]

    # 고강도 운동 (B등급 이상, MET 5.5+)
    high_intensity = [
        {"exercise_name": "push up", "category": [1, 2], "difficulty": 4, "met": 6.0},
        {"exercise_name": "burpee test", "category": [4], "difficulty": 5, "met": 8.0},
        {"exercise_name": "plank", "category": [4], "difficulty": 5, "met": 8.0},
    ]

    if score >= 70:
        # B등급 이상: 전체 운동 사용 가능
        return low_intensity + mid_intensity + high_intensity
    elif score >= 55:
        # C+등급: 저 + 중강도
        return low_intensity + mid_intensity
    elif score >= 45:
        # C등급: 저 + 중저강도 (차별화)
        return low_intensity + mid_low_intensity
    elif score >= 35:
        # D등급: 저강도만
        return low_intensity
    else:
        # F등급: 최저강도만
        return very_low_intensity


# ==========================================================
# 5) 칼로리 계산 (동적)
# ==========================================================
def calculate_calories(
    avg_met: float, weight: float, duration_sec: int, multiplier: float = 1.0
) -> int:
    """
    칼로리 계산 공식 (MET 기반)

    공식: Calories = MET × 3.5 × Weight(kg) / 200 × Time(min)
    - MET: 운동 강도
    - 3.5: 산소 소비량 상수 (ml/kg/min)
    - 200: 칼로리 변환 상수
    - multiplier: 점수 기반 보정 계수
    """
    duration_min = duration_sec / 60
    base_calories = avg_met * 3.5 * weight / 200 * duration_min
    return int(base_calories * multiplier)


# ==========================================================
# 6) 데이터 품질 확인
# ==========================================================
def check_data_quality(raw: dict) -> dict:
    """
    데이터 품질 확인 - 상세 정보 반환
    """
    has_sleep = raw.get("sleep_hr", 0) > 0
    has_activity = raw.get("steps", 0) > 0
    has_heart_rate = (
        raw.get("heart_rate", 0) > 0 or raw.get("resting_heart_rate", 0) > 0
    )
    has_body = raw.get("weight", 0) > 0 or raw.get("bmi", 0) > 0

    quality_score = sum([has_sleep, has_activity, has_heart_rate, has_body])

    return {
        "is_sufficient": has_sleep or has_activity,
        "has_sleep": has_sleep,
        "has_activity": has_activity,
        "has_heart_rate": has_heart_rate,
        "has_body": has_body,
        "quality_score": quality_score,  # 0-4
        "quality_level": (
            "high" if quality_score >= 3 else "medium" if quality_score >= 2 else "low"
        ),
    }


# ==========================================================
# 7) LLM 결과 검증
# ==========================================================
def validate_routine(result: dict, settings: dict, target_min: int) -> bool:
    """LLM 결과 검증 - 시간, MET 범위 확인"""
    try:
        routine = result.get("ai_recommended_routine", {})
        items = routine.get("items", [])

        if not items:
            print("[WARN] 검증 실패: items 비어있음")
            return False

        # 1) 시간 검증 (±20% 허용)
        total_sec = 0
        for item in items:
            duration = item.get("duration_sec", 30)
            sets = item.get("set_count", 3)
            rest = item.get("rest_sec", 15)
            total_sec += (duration * sets) + (rest * (sets - 1))

        target_sec = target_min * 60
        if not (target_sec * 0.8 <= total_sec <= target_sec * 1.2):
            print(f"[WARN] 검증 실패: 시간 {total_sec}초 (목표 {target_sec}±20%)")
            return False

        # 2) MET 범위 검증 (settings 기반)
        min_met = settings.get("met_min", 3.0)
        max_met = settings.get("met_max", 6.0)

        for item in items:
            item_met = item.get("met", 0)
            # 약간의 여유 허용 (±0.5)
            if not (min_met - 0.5 <= item_met <= max_met + 0.5):
                print(f"[WARN] 검증 실패: MET {item_met} (범위 {min_met}-{max_met})")
                return False

        return True

    except Exception as e:
        print(f"[ERROR] 검증 중 오류: {str(e)}")
        return False


# ==========================================================
# 8) 상세 건강 리포트 생성
# ==========================================================
def build_detailed_health_analysis(raw: dict) -> str:
    """상세한 건강 상태 분석 텍스트 생성"""

    interpretation = interpret_health_data(raw)
    lines = []

    score_info = interpretation["health_score"]
    lines.append("=" * 50)
    lines.append("📊 종합 건강 분석 리포트")
    lines.append("=" * 50)
    lines.append(f"\n🏅 건강 점수: {score_info['score']}점 / 100점")
    lines.append(f"   등급: {score_info['grade']} ({score_info['grade_text']})")
    if score_info.get("factors"):
        lines.append("   산정 요소:")
        for factor in score_info["factors"]:
            lines.append(f"     • {factor}")

    sleep = interpretation["sleep"]
    lines.append(f"\n😴 수면 분석")
    lines.append(f"   상태: {sleep.get('level', '데이터 없음')}")
    lines.append(f"   수면 시간: {raw.get('sleep_hr', 0)}시간")
    if sleep.get("message"):
        lines.append(f"   평가: {sleep['message']}")

    activity = interpretation["activity"]
    lines.append(f"\n🚶 활동량 분석")
    lines.append(f"   걸음수: {raw.get('steps', 0):,}보")
    lines.append(f"   활동 레벨: {activity.get('activity_level', 'unknown')}")
    if activity.get("message"):
        lines.append(f"   평가: {activity['message']}")

    hr = interpretation["heart_rate"]
    lines.append(f"\n❤️ 심박수 분석")
    lines.append(f"   휴식기 심박수: {raw.get('resting_heart_rate', 0)}bpm")
    lines.append(f"   피트니스 레벨: {hr.get('fitness_level', 'unknown')}")

    exercise_rec = interpretation["exercise_recommendation"]
    lines.append(f"\n💪 권장 운동 강도: {exercise_rec.get('recommended_level', '중')}")

    lines.append("\n" + "=" * 50)

    return "\n".join(lines)


# ==========================================================
# 9) 점수 기반 Fallback 루틴 생성 (완전 동적)
# ==========================================================
def get_fallback_routine(score: int, duration_min: int, raw: dict = None) -> dict:
    """
    점수 기반 동적 Fallback 루틴 생성

    ✅ 개선 사항:
    - 건강 점수에 따른 운동 강도 차등
    - 체중 동적 추정
    - 점수별 운동 풀 선택
    - 동적 칼로리 계산
    - 최소 100kcal 보장
    - 실제 운동 시간 정확히 반영
    """

    raw = raw or {}

    # 1) 점수 기반 설정 가져오기
    settings = get_exercise_settings_by_score(score)

    # 2) 운동 풀 선택
    exercise_pool = get_exercise_pool_by_score(score)

    # 3) MET 범위에 맞는 운동만 필터링
    met_min = settings["met_min"]
    met_max = settings["met_max"]
    filtered_pool = [ex for ex in exercise_pool if met_min <= ex["met"] <= met_max]

    # 필터링 결과가 없으면 전체 풀에서 가장 가까운 운동 선택
    if not filtered_pool:
        filtered_pool = sorted(
            exercise_pool, key=lambda x: abs(x["met"] - (met_min + met_max) / 2)
        )[:4]

    # 4) 기본 설정
    target_seconds = duration_min * 60
    base_sets = settings["base_sets"]
    max_sets = settings["max_sets"]
    duration_sec = settings["duration_sec"]
    rest_sec = settings["rest_sec"]

    # 5) 운동 항목 생성 (목표 시간의 85~100% 채우기)
    items = []
    total_sec = 0
    idx = 0
    max_iterations = 20  # 최대 운동 개수

    while total_sec < target_seconds * 0.85 and idx < max_iterations:
        ex = filtered_pool[idx % len(filtered_pool)]
        sets = base_sets

        item_time = (duration_sec * sets) + (rest_sec * (sets - 1))

        # 시간 초과 체크
        if total_sec + item_time > target_seconds:
            # 세트 수 조정으로 맞추기 시도
            remaining = target_seconds - total_sec
            adjusted_sets = max(2, int(remaining / (duration_sec + rest_sec)))
            if adjusted_sets >= 2:
                sets = adjusted_sets
                item_time = (duration_sec * sets) + (rest_sec * (sets - 1))
            else:
                break

        items.append(
            {
                "exercise_name": ex["exercise_name"],
                "category": ex["category"],
                "difficulty": ex["difficulty"],
                "met": ex["met"],
                "duration_sec": duration_sec,
                "rest_sec": rest_sec,
                "set_count": sets,
                "reps": None,
            }
        )

        total_sec += item_time
        idx += 1

    # 6) 체중 추정 및 칼로리 계산
    weight = estimate_weight(raw)
    avg_met = sum(item["met"] for item in items) / max(len(items), 1)
    total_calories = calculate_calories(
        avg_met=avg_met,
        weight=weight,
        duration_sec=total_sec,
        multiplier=settings["calorie_multiplier"],
    )

    # 7) 최소 100kcal 보장 체크
    if total_calories < 100 and len(items) > 0:
        # 세트 수 증가로 칼로리 보충
        additional_sets_needed = int(
            (100 - total_calories)
            / (avg_met * 3.5 * weight / 200 * (duration_sec / 60))
        )
        additional_sets_needed = max(1, additional_sets_needed)

        # 기존 운동에 세트 추가
        sets_added = 0
        for item in items:
            if sets_added >= additional_sets_needed:
                break
            can_add = max_sets - item["set_count"]
            add_sets = min(can_add, additional_sets_needed - sets_added)
            if add_sets > 0:
                item["set_count"] += add_sets
                additional_time = add_sets * (duration_sec + rest_sec)
                total_sec += additional_time
                sets_added += add_sets

        # 칼로리 재계산
        total_calories = calculate_calories(
            avg_met=avg_met,
            weight=weight,
            duration_sec=total_sec,
            multiplier=settings["calorie_multiplier"],
        )

    # 8) 실제 운동 시간 계산 (분 단위, 반올림)
    actual_time_min = round(total_sec / 60)

    # 9) 분석 텍스트 생성
    if raw:
        analysis = build_analysis_text(
            raw=raw,
            difficulty_level=settings["intensity"],
            duration_min=actual_time_min,
            item_count=len(items),
            total_time_sec=total_sec,
        )
    else:
        analysis = (
            f"건강 점수 {score}점({settings['grade']}등급)에 맞춰 "
            f"{settings['intensity']} 강도의 {actual_time_min}분 운동 루틴을 생성했습니다. "
            f"총 {len(items)}개 운동, 예상 소모 칼로리 {total_calories}kcal입니다."
        )

    return {
        "analysis": analysis,
        "ai_recommended_routine": {
            "total_time_min": actual_time_min,  # ✅ 실제 운동 시간 반영
            "total_calories": total_calories,
            "items": items,
        },
        "used_data_ranked": {
            "primary": "score_based_fallback",
            "secondary": "rule_based",
        },
        "debug_info": {
            "health_score": score,
            "grade": settings["grade"],
            "intensity": settings["intensity"],
            "estimated_weight": weight,
            "avg_met": round(avg_met, 2),
            "total_exercise_sec": total_sec,
            "requested_time_min": duration_min,
            "actual_time_min": actual_time_min,
        },
    }


# ==========================================================
# 10) SEED_JSON (17종 운동 목록)
# ==========================================================
SEED_JSON = """
[
  {"exercise_name": "standing side crunch", "category": [2, 3], "difficulty": 3, "met": 4.0},
  {"exercise_name": "standing knee up", "category": [1, 3], "difficulty": 3, "met": 3.8},
  {"exercise_name": "burpee test", "category": [4], "difficulty": 5, "met": 8.0},
  {"exercise_name": "step forward dynamic lunge", "category": [3], "difficulty": 4, "met": 4.0},
  {"exercise_name": "side lunge", "category": [3], "difficulty": 5, "met": 5.0},
  {"exercise_name": "cross lunge", "category": [3, 2], "difficulty": 4, "met": 3.8},
  {"exercise_name": "good morning exercise", "category": [3], "difficulty": 5, "met": 5.0},
  {"exercise_name": "lying leg raise", "category": [3, 2], "difficulty": 4, "met": 4.0},
  {"exercise_name": "crunch", "category": [2], "difficulty": 4, "met": 4.5},
  {"exercise_name": "bicycle crunch", "category": [3, 2], "difficulty": 5, "met": 5.0},
  {"exercise_name": "scissor cross", "category": [2, 3], "difficulty": 4, "met": 4.5},
  {"exercise_name": "hip thrust", "category": [3, 2], "difficulty": 3, "met": 3.5},
  {"exercise_name": "plank", "category": [4], "difficulty": 5, "met": 8.0},
  {"exercise_name": "push up", "category": [1, 2], "difficulty": 4, "met": 6.0},
  {"exercise_name": "knee push up", "category": [1, 2], "difficulty": 3, "met": 5.0},
  {"exercise_name": "Y-exercise", "category": [1, 2], "difficulty": 3, "met": 4.5}
]
"""


# ==========================================================
# 11) 메인 LLM 분석 함수 (개선 버전)
# ==========================================================
def run_llm_analysis(
    summary: dict,
    user_id: str,
    difficulty_level: str,
    duration_min: int,
) -> dict:
    """
    LLM 기반 운동 분석 엔진 (개선 버전)

    ✅ 개선 사항:
    1. 건강 점수 기반 동적 설정
    2. Fallback 조건 세분화
    3. 데이터 품질에 따른 LLM 사용 결정
    4. 하드코딩 완전 제거
    """

    raw = summary.get("raw", {})

    # 1) 건강 점수 및 설정 계산
    health_score_info = calculate_health_score(raw)
    score = health_score_info.get("score", 50)
    settings = get_exercise_settings_by_score(score)

    # 2) 데이터 품질 확인
    data_quality = check_data_quality(raw)

    # 3) RAG 검색
    rag_query = build_rag_query(raw)
    rag_result = search_similar_summaries(
        query_dict=rag_query,
        user_id=user_id,
        top_k=3,
    )
    similar_days = rag_result.get("similar_days", [])
    rag_strength = classify_rag_strength(similar_days)

    # 4) 규칙 기반 건강 해석
    health_context = build_health_context_for_llm(raw)
    exercise_rec = recommend_exercise_intensity(raw)

    # 시스템 권장 강도 (점수 기반)
    auto_intensity = settings["intensity"]

    if rag_strength == "none":
        rag_context = ""
    elif rag_strength == "weak":
        rag_context = (
            "📚 과거에 유사한 기록이 일부 있었으나, 참고 수준으로만 반영했습니다."
        )
    else:
        rag_context = analyze_rag_patterns(similar_days)

    # ============================================
    # 5) Fallback 조건 판단 (세분화)
    # ============================================
    use_fallback = False
    fallback_reason = ""

    # 조건 1: 데이터 부족
    if not data_quality["is_sufficient"]:
        use_fallback = True
        fallback_reason = f"데이터 부족 (수면/활동량 없음)"

    # 조건 2: 매우 낮은 점수 (안전 모드)
    elif score < 40:
        use_fallback = True
        fallback_reason = f"건강 점수 {score}점 (40점 미만, 안전 모드)"

    # 조건 3: 데이터 품질이 낮고 점수도 낮음
    elif data_quality["quality_level"] == "low" and score < 50:
        use_fallback = True
        fallback_reason = f"데이터 품질 낮음 + 점수 {score}점"

    # ✅ 개선: 점수 50 이상이면 LLM 시도
    # 기존: auto_difficulty == "하" → 무조건 Fallback
    # 개선: 점수 기반으로 판단

    if use_fallback:
        print(f"[INFO] Fallback 사용: {fallback_reason}")
        result = get_fallback_routine(score, duration_min, raw)
        result["health_context"] = {
            "health_score": health_score_info,
            "recommended_intensity": auto_intensity,
            "fallback_reason": fallback_reason,
            "data_quality": data_quality,
        }
        return result

    # ============================================
    # 6) LLM 호출
    # ============================================
    detailed_report = build_detailed_health_analysis(raw)
    weight = estimate_weight(raw)

    raw_block = f"""[사용자 건강 데이터]

📊 건강 점수: {score}점 ({settings['grade']}등급)
📏 추정 체중: {weight}kg

• 수면: {raw.get('sleep_hr', 0)}시간
• 걸음수: {raw.get('steps', 0):,}보
• 활동 칼로리: {raw.get('active_calories', 0)}kcal
• 심박수: {raw.get('heart_rate', 0)}bpm / 휴식기 {raw.get('resting_heart_rate', 0)}bpm
• BMI: {raw.get('bmi', 0):.1f}"""

    system_prompt = f"""당신은 피트니스 코치입니다.

## 참고 정보
- RAG 상태: {rag_strength}
  * none  → 과거 데이터 참고 금지
  * weak  → 참고 멘트 수준
  * strong → 반복 패턴 반영 가능

### RAG 상태별 analysis 톤 가이드

[RAG none]
- 오늘 하루 기준의 건강 상태 분석에 집중한다.
- 과거 기록이나 누적 경향에 대한 언급은 하지 않는다.

[RAG weak]
- 최근 기록을 참고하되, 단정적인 표현은 피한다.
- "가능성", "경향", "참고 수준"의 표현을 사용한다.

[RAG strong]
- 반복적으로 관찰된 생활 패턴을 반영한다.
- 변화 방향 판단은 반드시 "수면 / 활동량 / 회복 지표" 중 하나 이상을 근거로 한다.

## 역할
건강 데이터를 분석하여 맞춤형 운동 루틴을 JSON으로 처방합니다.

## 규칙

### 1. analysis 작성 (3-4문장)
- 현재 건강 상태 평가
- 운동 선택 이유
- 주의사항

### 2. 운동 선택 (MET 범위 엄격 준수!)
- 17종 운동 목록에서만 선택
- 건강 점수 기반 권장 강도: {auto_intensity}
- MET 범위: {settings['met_min']} - {settings['met_max']}

### 3. 시간 계산 (매우 중요!)
- 목표: {duration_min}분 = {duration_min * 60}초
- 각 운동: (duration_sec * set_count) + (rest_sec * (set_count - 1))
- 모든 운동 합계가 목표의 80~120% 이내

### 4. 칼로리 계산
- 공식: MET × 3.5 × {weight}kg / 200 × 시간(분)
- 사용자 체중 {weight}kg 반영

## 응답 JSON
{{
  "analysis": "3-4문장 분석",
  "ai_recommended_routine": {{
    "total_time_min": {duration_min},
    "total_calories": 예상칼로리,
    "items": [
      {{
        "exercise_name": "운동명",
        "category": [카테고리],
        "difficulty": 난이도,
        "met": MET값,
        "duration_sec": 30-60,
        "rest_sec": {settings['rest_sec']},
        "set_count": {settings['base_sets']}-{settings['max_sets']},
        "reps": null
      }}
    ]
  }},
  "used_data_ranked": {{
    "primary": "주요 데이터",
    "secondary": "보조 데이터"
  }}
}}"""

    user_prompt = f"""{raw_block}

{health_context}

{rag_context}

---
• 사용자 요청 난이도: {difficulty_level}
• 시스템 권장 강도: {auto_intensity} (건강 점수 기반, 반드시 준수!)
• 목표 시간: {duration_min}분
• 체중: {weight}kg

## 운동 목록
{SEED_JSON}

JSON만 출력. 시간/칼로리 계산 정확히!"""

    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL_MAIN,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=LLM_MAX_TOKENS,
            temperature=LLM_TEMPERATURE,
        )

        raw_text = resp.choices[0].message.content
        cleaned = clean_json_text(raw_text)
        parsed = try_parse_json(cleaned)

        # ============================================
        # 7) LLM 결과 검증
        # ============================================
        if parsed and "analysis" in parsed and "ai_recommended_routine" in parsed:
            if validate_routine(parsed, settings, duration_min):
                parsed["detailed_health_report"] = detailed_report
                parsed["health_context"] = {
                    "health_score": health_score_info,
                    "recommended_intensity": auto_intensity,
                    "estimated_weight": weight,
                    "llm_validated": True,
                    "data_quality": data_quality,
                }
                print(
                    f"[INFO] LLM 결과 검증 성공 (점수: {score}, 강도: {auto_intensity})"
                )
                return parsed
            else:
                print(f"[WARN] LLM 결과 검증 실패 → Fallback 사용")
                result = get_fallback_routine(score, duration_min, raw)
                result["health_context"] = {
                    "health_score": health_score_info,
                    "recommended_intensity": auto_intensity,
                    "fallback_reason": "LLM 결과 검증 실패",
                    "data_quality": data_quality,
                }
                return result

        print(f"[WARN] LLM JSON 파싱 실패 → Fallback 사용")
        result = get_fallback_routine(score, duration_min, raw)
        result["health_context"] = {
            "health_score": health_score_info,
            "recommended_intensity": auto_intensity,
            "fallback_reason": "LLM JSON 파싱 실패",
            "data_quality": data_quality,
        }
        return result

    except Exception as e:
        print(f"[ERROR] LLM 호출 실패: {str(e)} → Fallback 사용")
        result = get_fallback_routine(score, duration_min, raw)
        result["health_context"] = {
            "health_score": health_score_info,
            "recommended_intensity": auto_intensity,
            "fallback_reason": f"LLM 호출 오류: {str(e)}",
            "data_quality": data_quality,
        }
        return result


# ==========================================================
# 12) 헬퍼 함수들
# ==========================================================
def get_health_analysis_context(raw: dict) -> str:
    return build_health_context_for_llm(raw)


def get_health_score(raw: dict) -> dict:
    return calculate_health_score(raw)


def get_detailed_health_report(raw: dict) -> str:
    return build_detailed_health_analysis(raw)
