from app.core.health_interpreter import (
    calculate_health_score,
    recommend_exercise_intensity,
)


def build_rag_query(raw: dict) -> dict:
    """
    RAG 검색용 query dict 생성

    목적:
    - 벡터 검색에 적합한 '의미 요약' 생성
    - 수치 원본이 아니라 상태/판단 중심
    """

    health_score = calculate_health_score(raw)
    exercise_rec = recommend_exercise_intensity(raw)

    steps = raw.get("steps", 0)

    if steps <= 0:
        activity_level = "unknown"
    elif steps < 5000:
        activity_level = "low"
    elif steps < 10000:
        activity_level = "moderate"
    else:
        activity_level = "high"

    return {
        # 컨디션 축
        "sleep_hr": raw.get("sleep_hr", 0),
        "steps": steps,
        "activity_level": activity_level,
        # 시스템 판단 축
        "health_score": health_score.get("score", 50),
        "health_grade": health_score.get("grade", "C"),
        # 처방 축
        "recommended_intensity": exercise_rec.get("recommended_level", "중"),
    }


def classify_rag_strength(similar_days: list) -> str:
    """
    RAG 결과의 신뢰 수준 분류
    """
    if not similar_days:
        return "none"

    if len(similar_days) == 1:
        raw = similar_days[0].get("raw", {})
        has_core = raw.get("sleep_hr", 0) > 0 or raw.get("steps", 0) > 0
        return "weak" if not has_core else "medium"

    return "strong"
