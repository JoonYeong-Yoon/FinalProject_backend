"""
Health Interpreter - 규칙 기반 건강 상태 해석기 (v7)
포함: build_health_context_for_llm, build_analysis_text
"""

from typing import Dict, List, Tuple


# ============================================================
# 1) 수면 분석
# ============================================================
def interpret_sleep(raw: dict) -> dict:
    """수면 상태 해석"""
    sleep_hr = raw.get("sleep_hr", 0)
    sleep_min = raw.get("sleep_min", 0)

    if sleep_hr <= 0:
        return {
            "status": "unknown",
            "level": "데이터 없음",
            "message": "수면 데이터가 기록되지 않았습니다.",
            "recommendation": "수면 추적을 활성화해주세요.",
            "exercise_impact": "neutral",
        }

    if sleep_hr < 5:
        return {
            "status": "critical",
            "level": "심각한 수면 부족",
            "message": f"{sleep_hr}시간 수면은 매우 부족합니다. 피로 누적 위험이 높습니다.",
            "recommendation": "고강도 운동을 피하고 가벼운 스트레칭만 권장합니다.",
            "exercise_impact": "reduce_intensity",
            "intensity_modifier": 0.5,
        }
    elif sleep_hr < 6:
        return {
            "status": "warning",
            "level": "수면 부족",
            "message": f"{sleep_hr}시간 수면으로 약간 부족합니다.",
            "recommendation": "중강도 운동을 권장하며, 무리하지 마세요.",
            "exercise_impact": "reduce_intensity",
            "intensity_modifier": 0.7,
        }
    elif sleep_hr < 7:
        return {
            "status": "fair",
            "level": "보통",
            "message": f"{sleep_hr}시간 수면으로 괜찮은 편입니다.",
            "recommendation": "일반적인 운동 루틴을 수행할 수 있습니다.",
            "exercise_impact": "normal",
            "intensity_modifier": 0.9,
        }
    elif sleep_hr <= 9:
        return {
            "status": "good",
            "level": "충분한 수면",
            "message": f"{sleep_hr}시간의 충분한 수면을 취했습니다.",
            "recommendation": "컨디션이 좋으니 적극적인 운동이 가능합니다.",
            "exercise_impact": "boost",
            "intensity_modifier": 1.0,
        }
    else:
        return {
            "status": "over",
            "level": "과다 수면",
            "message": f"{sleep_hr}시간 수면은 다소 많습니다.",
            "recommendation": "가벼운 유산소로 몸을 깨워주세요.",
            "exercise_impact": "cardio_focus",
            "intensity_modifier": 0.85,
        }


# ============================================================
# 2) 심박수 분석
# ============================================================
def interpret_heart_rate(raw: dict) -> dict:
    """심박수 상태 해석"""
    hr = raw.get("heart_rate", 0)
    resting_hr = raw.get("resting_heart_rate", 0)

    result = {
        "avg_hr": hr,
        "resting_hr": resting_hr,
        "status": "unknown",
        "fitness_level": "unknown",
        "message": "",
        "exercise_impact": "neutral",
    }

    if resting_hr <= 0 and hr <= 0:
        result["message"] = "심박수 데이터가 없습니다."
        return result

    if resting_hr > 0:
        if resting_hr < 50:
            result["fitness_level"] = "athlete"
            result["message"] = f"휴식기 심박수 {resting_hr}bpm은 운동선수 수준입니다."
            result["exercise_impact"] = "high_intensity_ok"
        elif resting_hr < 60:
            result["fitness_level"] = "excellent"
            result["message"] = (
                f"휴식기 심박수 {resting_hr}bpm은 매우 건강한 수준입니다."
            )
            result["exercise_impact"] = "high_intensity_ok"
        elif resting_hr < 70:
            result["fitness_level"] = "good"
            result["message"] = f"휴식기 심박수 {resting_hr}bpm은 양호한 수준입니다."
            result["exercise_impact"] = "normal"
        elif resting_hr < 80:
            result["fitness_level"] = "average"
            result["message"] = f"휴식기 심박수 {resting_hr}bpm은 평균 수준입니다."
            result["exercise_impact"] = "normal"
        elif resting_hr < 90:
            result["fitness_level"] = "below_average"
            result["message"] = (
                f"휴식기 심박수 {resting_hr}bpm은 다소 높습니다. 유산소 운동을 늘려보세요."
            )
            result["exercise_impact"] = "cardio_focus"
        else:
            result["fitness_level"] = "poor"
            result["message"] = (
                f"휴식기 심박수 {resting_hr}bpm은 높은 편입니다. 저강도 운동부터 시작하세요."
            )
            result["exercise_impact"] = "low_intensity"
            result["status"] = "warning"

    return result


# ============================================================
# 3) 활동량 분석
# ============================================================
def interpret_activity(raw: dict) -> dict:
    """활동량 상태 해석"""
    steps = raw.get("steps", 0)
    distance_km = raw.get("distance_km", 0)
    active_cal = raw.get("active_calories", 0)
    exercise_min = raw.get("exercise_min", 0)

    result = {
        "steps": steps,
        "distance_km": distance_km,
        "active_calories": active_cal,
        "exercise_min": exercise_min,
        "activity_level": "unknown",
        "message": "",
        "recommendation": "",
    }

    if steps <= 0:
        result["activity_level"] = "no_data"
        result["message"] = "활동 데이터가 기록되지 않았습니다."
    elif steps < 3000:
        result["activity_level"] = "sedentary"
        result["message"] = f"오늘 {steps:,}보로 매우 적은 활동량입니다."
        result["recommendation"] = (
            "기본적인 움직임을 늘려보세요. 전신 운동을 추천합니다."
        )
    elif steps < 5000:
        result["activity_level"] = "low"
        result["message"] = f"오늘 {steps:,}보로 활동량이 부족합니다."
        result["recommendation"] = "유산소 운동을 추가하면 좋겠습니다."
    elif steps < 7500:
        result["activity_level"] = "moderate"
        result["message"] = f"오늘 {steps:,}보로 적당한 활동량입니다."
        result["recommendation"] = "균형 잡힌 운동 루틴이 적합합니다."
    elif steps < 10000:
        result["activity_level"] = "active"
        result["message"] = f"오늘 {steps:,}보로 활발한 하루입니다."
        result["recommendation"] = "근력 운동에 집중해도 좋습니다."
    else:
        result["activity_level"] = "very_active"
        result["message"] = f"오늘 {steps:,}보로 매우 활동적인 하루입니다!"
        result["recommendation"] = (
            "이미 충분한 활동을 했으니 스트레칭과 회복에 집중하세요."
        )

    return result


# ============================================================
# 4) BMI 분석
# ============================================================
def interpret_bmi(raw: dict) -> dict:
    """BMI 상태 해석"""
    bmi = raw.get("bmi", 0)
    weight = raw.get("weight", 0)
    height_m = raw.get("height_m", 0)

    result = {
        "bmi": bmi,
        "weight": weight,
        "height_m": height_m,
        "category": "unknown",
        "message": "",
        "exercise_focus": [],
    }

    if bmi <= 0:
        result["message"] = "BMI 데이터가 없습니다."
        return result

    if bmi < 18.5:
        result["category"] = "underweight"
        result["message"] = f"BMI {bmi:.1f}로 저체중입니다."
        result["exercise_focus"] = ["근력 운동", "고단백 식이와 함께 웨이트 트레이닝"]
    elif bmi < 23:
        result["category"] = "normal"
        result["message"] = f"BMI {bmi:.1f}로 정상 체중입니다."
        result["exercise_focus"] = ["균형 잡힌 전신 운동", "유산소와 근력 병행"]
    elif bmi < 25:
        result["category"] = "overweight"
        result["message"] = f"BMI {bmi:.1f}로 과체중입니다."
        result["exercise_focus"] = ["유산소 운동 강화", "HIIT", "칼로리 소모 중심"]
    elif bmi < 30:
        result["category"] = "obese_1"
        result["message"] = f"BMI {bmi:.1f}로 비만 1단계입니다."
        result["exercise_focus"] = [
            "저충격 유산소",
            "관절 부담 적은 운동",
            "수영/자전거 추천",
        ]
    else:
        result["category"] = "obese_2"
        result["message"] = f"BMI {bmi:.1f}로 비만 2단계 이상입니다."
        result["exercise_focus"] = [
            "걷기 중심",
            "저강도 꾸준한 운동",
            "전문가 상담 권장",
        ]

    return result


# ============================================================
# 5) 산소포화도 분석
# ============================================================
def interpret_oxygen(raw: dict) -> dict:
    """산소포화도 해석"""
    oxygen = raw.get("oxygen_saturation", 0)

    if oxygen <= 0:
        return {"status": "unknown", "message": "산소포화도 데이터가 없습니다."}

    if oxygen >= 98:
        return {
            "status": "excellent",
            "message": f"산소포화도 {oxygen}%로 매우 우수합니다.",
        }
    elif oxygen >= 95:
        return {"status": "normal", "message": f"산소포화도 {oxygen}%로 정상입니다."}
    elif oxygen >= 90:
        return {
            "status": "low",
            "message": f"산소포화도 {oxygen}%로 다소 낮습니다. 호흡 운동을 권장합니다.",
        }
    else:
        return {
            "status": "critical",
            "message": f"산소포화도 {oxygen}%로 매우 낮습니다. 의료 상담을 권장합니다.",
        }


# ============================================================
# 6) 종합 건강 점수 계산 (0-100)
# ============================================================
def calculate_health_score(raw: dict) -> dict:
    """규칙 기반 종합 건강 점수 계산"""
    score = 50
    factors = []

    # 수면 점수 (최대 ±15점)
    sleep_hr = raw.get("sleep_hr", 0)
    if sleep_hr > 0:
        if 7 <= sleep_hr <= 9:
            score += 15
            factors.append("충분한 수면 (+15)")
        elif 6 <= sleep_hr < 7:
            score += 8
            factors.append("적정 수면 (+8)")
        elif sleep_hr < 5:
            score -= 10
            factors.append("심각한 수면 부족 (-10)")
        elif sleep_hr < 6:
            score -= 5
            factors.append("수면 부족 (-5)")

    # 활동량 점수 (최대 ±15점)
    steps = raw.get("steps", 0)
    if steps >= 10000:
        score += 15
        factors.append("활발한 활동량 (+15)")
    elif steps >= 7500:
        score += 10
        factors.append("적정 활동량 (+10)")
    elif steps >= 5000:
        score += 5
        factors.append("보통 활동량 (+5)")
    elif steps > 0 and steps < 3000:
        score -= 5
        factors.append("낮은 활동량 (-5)")

    # 심박수 점수 (최대 ±10점)
    resting_hr = raw.get("resting_heart_rate", 0)
    if resting_hr > 0:
        if resting_hr < 60:
            score += 10
            factors.append("우수한 심폐 기능 (+10)")
        elif resting_hr < 70:
            score += 5
            factors.append("양호한 심폐 기능 (+5)")
        elif resting_hr > 85:
            score -= 5
            factors.append("높은 휴식기 심박수 (-5)")

    # BMI 점수 (최대 ±10점)
    bmi = raw.get("bmi", 0)
    if bmi > 0:
        if 18.5 <= bmi < 23:
            score += 10
            factors.append("정상 체중 (+10)")
        elif 23 <= bmi < 25:
            score += 3
            factors.append("약간 과체중 (+3)")
        elif bmi < 18.5:
            score -= 3
            factors.append("저체중 (-3)")
        elif bmi >= 25:
            score -= 5
            factors.append("비만 (-5)")

    # 산소포화도 점수 (최대 ±5점)
    oxygen = raw.get("oxygen_saturation", 0)
    if oxygen >= 98:
        score += 5
        factors.append("우수한 산소포화도 (+5)")
    elif oxygen > 0 and oxygen < 95:
        score -= 5
        factors.append("낮은 산소포화도 (-5)")

    score = max(0, min(100, score))

    if score >= 85:
        grade, grade_text = "A", "매우 우수"
    elif score >= 70:
        grade, grade_text = "B", "양호"
    elif score >= 55:
        grade, grade_text = "C", "보통"
    elif score >= 40:
        grade, grade_text = "D", "개선 필요"
    else:
        grade, grade_text = "F", "주의 필요"

    return {
        "score": score,
        "grade": grade,
        "grade_text": grade_text,
        "factors": factors,
    }


# ============================================================
# 7) 운동 강도 추천 (안전 우선 로직)
# ============================================================
def recommend_exercise_intensity(raw: dict) -> dict:
    """건강 데이터 기반 운동 강도 추천 - 안전 우선 로직"""

    sleep_info = interpret_sleep(raw)
    hr_info = interpret_heart_rate(raw)
    activity_info = interpret_activity(raw)
    health_score_info = calculate_health_score(raw)

    base_intensity = 1.0
    reasons = []

    # 1) 건강 점수 기반 조정
    score = health_score_info.get("score", 50)
    if score < 40:
        base_intensity *= 0.5
        reasons.append(f"건강 점수 {score}점(F등급)으로 저강도 필수")
    elif score < 55:
        base_intensity *= 0.6
        reasons.append(f"건강 점수 {score}점(D등급)으로 강도 40% 감소")
    elif score < 70:
        base_intensity *= 0.8
        reasons.append(f"건강 점수 {score}점(C등급)으로 강도 20% 감소")

    # 2) 수면 영향
    if "intensity_modifier" in sleep_info:
        modifier = sleep_info["intensity_modifier"]
        if modifier < 1.0:
            base_intensity *= modifier
            reasons.append(f"수면 부족으로 강도 {int((1-modifier)*100)}% 감소")

    # 3) 심박수 영향
    if hr_info.get("exercise_impact") == "low_intensity":
        base_intensity *= 0.7
        reasons.append("높은 휴식기 심박수로 강도 30% 감소")

    if hr_info.get("resting_hr", 0) == 0 and hr_info.get("avg_hr", 0) == 0:
        base_intensity = min(base_intensity, 0.75)
        reasons.append("심박수 데이터 없음 → 안전상 중강도 이하 권장")

    # 4) 활동량 영향
    activity_level = activity_info.get("activity_level", "unknown")

    if activity_level == "sedentary":
        base_intensity *= 0.5
        reasons.append("활동량 매우 부족 → 저강도부터 시작 권장")
    elif activity_level == "low":
        base_intensity *= 0.65
        reasons.append("활동량 부족 → 강도 35% 감소")
    elif activity_level == "very_active":
        base_intensity *= 0.85
        reasons.append("이미 높은 활동량 → 강도 15% 감소 (회복 고려)")

    # 5) 최종 강도 레벨 결정
    if base_intensity >= 0.85:
        level, met_range, description = "상", "MET 5-8", "고강도 운동 가능"
    elif base_intensity >= 0.6:
        level, met_range, description = "중", "MET 4-5", "중강도 운동 권장"
    else:
        level, met_range, description = "하", "MET 2.5-4", "저강도 운동 권장"

    return {
        "recommended_level": level,
        "intensity_score": round(base_intensity, 2),
        "met_range": met_range,
        "description": description,
        "reasons": reasons,
        "health_score": score,
        "sleep_status": sleep_info.get("level", ""),
        "activity_status": activity_level,
    }


# ============================================================
# 8) 종합 해석 (메인 함수)
# ============================================================
def interpret_health_data(raw: dict) -> dict:
    """건강 데이터 종합 해석 - LLM 호출 없이 규칙 기반"""
    return {
        "sleep": interpret_sleep(raw),
        "heart_rate": interpret_heart_rate(raw),
        "activity": interpret_activity(raw),
        "bmi": interpret_bmi(raw),
        "oxygen": interpret_oxygen(raw),
        "health_score": calculate_health_score(raw),
        "exercise_recommendation": recommend_exercise_intensity(raw),
    }


# ============================================================
# 9) Fallback용 상세 분석 텍스트 생성
# ============================================================
def build_analysis_text(
    raw: dict,
    difficulty_level: str,
    duration_min: int,
    item_count: int,
    total_time_sec: int,
) -> str:
    """규칙 기반 상세 분석 텍스트 생성 (LLM 호출 없음)"""

    health_info = interpret_health_data(raw)
    score_info = health_info["health_score"]
    sleep_info = health_info["sleep"]
    activity_info = health_info["activity"]
    hr_info = health_info["heart_rate"]
    exercise_rec = health_info["exercise_recommendation"]

    lines = []

    # 1) 건강 점수 + 근거
    score = score_info["score"]
    grade = score_info["grade"]
    factors = score_info.get("factors", [])

    lines.append(f"📊 건강 점수 {score}점 ({grade}등급)")
    if factors:
        lines.append(f"   산정 근거: {', '.join(factors[:3])}")

    # 2) 주요 데이터 수치
    data_points = []

    sleep_hr = raw.get("sleep_hr", 0)
    if sleep_hr > 0:
        data_points.append(f"수면 {sleep_hr}시간({sleep_info.get('level', '')})")

    steps = raw.get("steps", 0)
    if steps > 0:
        data_points.append(
            f"걸음 {steps:,}보({activity_info.get('activity_level', '')})"
        )

    resting_hr = raw.get("resting_heart_rate", 0)
    if resting_hr > 0:
        data_points.append(f"휴식심박 {resting_hr}bpm")

    if data_points:
        lines.append(f"   측정 데이터: {', '.join(data_points)}")

    # 3) 운동 강도 추천 이유
    reasons = exercise_rec.get("reasons", [])
    rec_level = exercise_rec.get("recommended_level", difficulty_level)

    lines.append(f"\n💪 권장 강도: {rec_level}")
    if reasons:
        lines.append(f"   이유: {reasons[0]}")

    # 4) 운동 구성 요약
    difficulty_desc = {
        "하": "관절에 무리 없는 저강도 운동",
        "중": "체력 향상과 칼로리 소모 균형",
        "상": "최대 효과를 위한 고강도 운동",
    }

    lines.append(f"\n🏃 {difficulty_desc.get(difficulty_level, '')}으로 구성했습니다.")
    lines.append(f"   총 {item_count}개 운동, 약 {total_time_sec//60}분")

    return "\n".join(lines)


# ============================================================
# 10) LLM 프롬프트용 컨텍스트 생성
# ============================================================
def build_health_context_for_llm(raw: dict) -> str:
    """LLM 프롬프트에 포함할 건강 상태 컨텍스트 문자열 생성"""
    interpretation = interpret_health_data(raw)

    lines = []

    # 건강 점수
    score_info = interpretation["health_score"]
    lines.append(
        f"[종합 건강 점수] {score_info['score']}점 ({score_info['grade']}등급 - {score_info['grade_text']})"
    )

    # 수면 상태
    sleep_info = interpretation["sleep"]
    if sleep_info["status"] != "unknown":
        lines.append(f"[수면] {sleep_info['level']}: {sleep_info['message']}")

    # 심박수 상태
    hr_info = interpretation["heart_rate"]
    if hr_info["message"]:
        lines.append(f"[심박수] {hr_info['message']}")

    # 활동량 상태
    activity_info = interpretation["activity"]
    if activity_info["activity_level"] != "no_data":
        lines.append(f"[활동량] {activity_info['message']}")

    # BMI 상태
    bmi_info = interpretation["bmi"]
    if bmi_info["category"] != "unknown":
        lines.append(f"[체형] {bmi_info['message']}")
        if bmi_info["exercise_focus"]:
            lines.append(f"  → 권장: {', '.join(bmi_info['exercise_focus'])}")

    # 운동 강도 추천
    exercise_rec = interpretation["exercise_recommendation"]
    lines.append(
        f"[권장 운동 강도] {exercise_rec['recommended_level']} ({exercise_rec['met_range']})"
    )
    if exercise_rec["reasons"]:
        for reason in exercise_rec["reasons"]:
            lines.append(f"  - {reason}")

    return "\n".join(lines)


# ============================================================
# 11) RAG 유사 패턴 분석
# ============================================================
def analyze_rag_patterns(similar_days: list) -> str:
    """
    RAG에서 가져온 과거 유사 패턴을
    LLM 프롬프트용 '참고 텍스트'로 변환한다.

    ⚠️ 규칙
    - 판단하지 않는다
    - 지시하지 않는다
    - 참고 정보로만 서술한다
    """
    if not similar_days:
        return "📚 과거 유사 패턴 참고: 해당 없음"

    lines = ["📚 과거 유사 패턴 참고"]

    for i, day in enumerate(similar_days[:3], 1):
        date = day.get("date", "날짜 미상")
        raw = day.get("raw", {}) or {}

        sleep = raw.get("sleep_hr", 0)
        steps = raw.get("steps", 0)
        score = raw.get("health_score", None)

        summary_parts = []

        if sleep > 0:
            summary_parts.append(f"수면 {sleep}시간")
        if steps > 0:
            summary_parts.append(f"걸음수 {steps:,}보")
        if score:
            summary_parts.append(f"건강 점수 {score}점")

        if summary_parts:
            lines.append(f"- {date}: " + ", ".join(summary_parts))
        else:
            lines.append(f"- {date}: 주요 데이터 요약 불가")

    lines.append("※ 위 기록은 참고용이며, 현재 건강 데이터가 최우선입니다.")

    return "\n".join(lines)
