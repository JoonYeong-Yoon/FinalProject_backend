"""
calculate_health_score 함수 개선 패치

이 파일의 함수로 app/core/health_interpreter.py의
calculate_health_score 함수(270번 줄~365번 줄)를 교체하세요.

✅ 개선 사항:
1. 데이터 없음(0)은 감점하지 않음
2. 활동량 기준 완화 (3000~5000보는 중립)
3. heart_rate 활용 (resting_heart_rate 없으면 heart_rate 사용)
4. 등급 기준 조정 (더 세분화)
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
            "message": f"{sleep_hr:.1f}시간 수면은 매우 부족합니다. 피로 누적 위험이 높습니다.",
            "recommendation": "고강도 운동을 피하고 가벼운 스트레칭만 권장합니다.",
            "exercise_impact": "reduce_intensity",
            "intensity_modifier": 0.5,
        }
    elif sleep_hr < 6:
        return {
            "status": "warning",
            "level": "수면 부족",
            "message": f"{sleep_hr:.1f}시간 수면으로 약간 부족합니다.",
            "recommendation": "중강도 운동을 권장하며, 무리하지 마세요.",
            "exercise_impact": "reduce_intensity",
            "intensity_modifier": 0.7,
        }
    elif sleep_hr < 7:
        return {
            "status": "fair",
            "level": "보통",
            "message": f"{sleep_hr:.1f}시간 수면으로 괜찮은 편입니다.",
            "recommendation": "일반적인 운동 루틴을 수행할 수 있습니다.",
            "exercise_impact": "normal",
            "intensity_modifier": 0.9,
        }
    elif sleep_hr <= 9:
        return {
            "status": "good",
            "level": "충분한 수면",
            "message": f"{sleep_hr:.1f}시간의 충분한 수면을 취했습니다.",
            "recommendation": "컨디션이 좋으니 적극적인 운동이 가능합니다.",
            "exercise_impact": "boost",
            "intensity_modifier": 1.0,
        }
    else:
        return {
            "status": "over",
            "level": "과다 수면",
            "message": f"{sleep_hr:.1f}시간 수면은 다소 많습니다.",
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
        return {
            "status": "normal",
            "message": f"산소포화도 {oxygen}%로 정상 범위입니다.",
        }
    elif oxygen >= 90:
        return {
            "status": "warning",
            "message": f"산소포화도 {oxygen}%로 다소 낮습니다. 심호흡을 해보세요.",
        }
    else:
        return {
            "status": "critical",
            "message": f"산소포화도 {oxygen}%로 낮습니다. 전문의 상담을 권장합니다.",
        }


# ============================================================
# 6) 건강 점수 계산
# ============================================================
def calculate_health_score(raw: dict) -> dict:
    """
    규칙 기반 종합 건강 점수 계산 (0~100)

    ✅ 개선 사항:
    1. 데이터 없음(0)은 감점하지 않고 무시
    2. 활동량 기준 완화 (3000~5000보는 감점 아닌 중립)
    3. heart_rate 활용 (resting_heart_rate 없으면 heart_rate 사용)
    4. 점수 기준 세분화
    """
    score = 50  # 기본 점수
    factors = []

    # ========================================
    # 수면 점수 (최대 ±15점)
    # ========================================
    sleep_hr = raw.get("sleep_hr", 0)

    # 데이터가 있을 때만 평가
    if sleep_hr > 0:
        if 7 <= sleep_hr <= 9:
            score += 15
            factors.append("적정 수면 (+15)")
        elif 6 <= sleep_hr < 7:
            score += 10
            factors.append("양호한 수면 (+10)")
        elif 5 <= sleep_hr < 6:
            score += 3
            factors.append("약간 부족한 수면 (+3)")
        elif sleep_hr < 5:
            score -= 10
            factors.append("수면 부족 (-10)")
        elif sleep_hr > 9:
            score -= 3
            factors.append("과다 수면 (-3)")
    # sleep_hr == 0이면 데이터 없음으로 간주, 감점 없음

    # ========================================
    # 활동량 점수 (최대 ±15점)
    # ========================================
    steps = raw.get("steps", 0)

    # 데이터가 있을 때만 평가
    if steps > 0:
        if steps >= 10000:
            score += 15
            factors.append("활발한 활동량 (+15)")
        elif steps >= 8000:
            score += 12
            factors.append("좋은 활동량 (+12)")
        elif steps >= 6000:
            score += 8
            factors.append("적당한 활동량 (+8)")
        elif steps >= 4000:
            score += 5
            factors.append("보통 활동량 (+5)")
        elif steps >= 2000:
            score += 0  # 중립 (감점 없음)
            factors.append("낮은 활동량 (0)")
        else:  # steps < 2000
            score -= 5
            factors.append("매우 낮은 활동량 (-5)")
    # steps == 0이면 데이터 없음으로 간주, 감점 없음

    # ========================================
    # 심박수 점수 (최대 ±10점)
    # ========================================
    # resting_heart_rate 우선, 없으면 heart_rate 사용
    resting_hr = raw.get("resting_heart_rate", 0)
    if resting_hr == 0:
        # heart_rate가 있으면 참고 (일반 심박수는 휴식기보다 높음)
        heart_rate = raw.get("heart_rate", 0)
        if heart_rate > 0:
            # 일반 심박수는 휴식기보다 약 10~20 높다고 가정
            resting_hr = max(50, heart_rate - 15)

    if resting_hr > 0:
        if 50 <= resting_hr < 65:
            score += 10
            factors.append("우수한 심박수 (+10)")
        elif 65 <= resting_hr < 75:
            score += 7
            factors.append("건강한 심박수 (+7)")
        elif 75 <= resting_hr < 85:
            score += 3
            factors.append("정상 심박수 (+3)")
        elif 85 <= resting_hr < 95:
            score -= 3
            factors.append("약간 높은 심박수 (-3)")
        elif resting_hr >= 95:
            score -= 8
            factors.append("높은 심박수 (-8)")
    # resting_hr == 0이면 데이터 없음으로 간주, 감점 없음

    # ========================================
    # BMI 점수 (최대 ±10점)
    # ========================================
    bmi = raw.get("bmi", 0)

    if bmi > 0:
        if 18.5 <= bmi < 23:
            score += 10
            factors.append("정상 BMI (+10)")
        elif 23 <= bmi < 25:
            score += 5
            factors.append("약간 높은 BMI (+5)")
        elif 17 <= bmi < 18.5:
            score += 0
            factors.append("저체중 (0)")
        elif 25 <= bmi < 28:
            score -= 3
            factors.append("과체중 (-3)")
        elif 28 <= bmi < 30:
            score -= 5
            factors.append("비만 전단계 (-5)")
        elif bmi >= 30:
            score -= 8
            factors.append("비만 (-8)")
    # bmi == 0이면 데이터 없음으로 간주, 감점 없음

    # ========================================
    # 산소포화도 점수 (최대 ±5점)
    # ========================================
    oxygen = raw.get("oxygen_saturation", 0)

    if oxygen > 0:
        if oxygen >= 98:
            score += 5
            factors.append("우수한 산소포화도 (+5)")
        elif oxygen >= 95:
            score += 2
            factors.append("정상 산소포화도 (+2)")
        elif oxygen < 95:
            score -= 5
            factors.append("낮은 산소포화도 (-5)")
    # oxygen == 0이면 데이터 없음으로 간주, 감점 없음

    # ========================================
    # 활동 칼로리 보너스 (최대 +5점)
    # ========================================
    active_cal = raw.get("active_calories", 0)
    if active_cal >= 300:
        score += 5
        factors.append("높은 활동 칼로리 (+5)")
    elif active_cal >= 150:
        score += 2
        factors.append("적당한 활동 칼로리 (+2)")

    # ========================================
    # 운동 시간 보너스 (최대 +5점)
    # ========================================
    exercise_min = raw.get("exercise_min", 0)
    if exercise_min >= 30:
        score += 5
        factors.append("충분한 운동 시간 (+5)")
    elif exercise_min >= 15:
        score += 2
        factors.append("적당한 운동 시간 (+2)")

    # ========================================
    # 점수 범위 제한 및 등급 산정
    # ========================================
    score = max(0, min(100, score))

    # 등급 기준 (세분화)
    if score >= 80:
        grade, grade_text = "A", "매우 우수"
    elif score >= 70:
        grade, grade_text = "B+", "우수"
    elif score >= 60:
        grade, grade_text = "B", "양호"
    elif score >= 55:
        grade, grade_text = "C+", "보통 이상"
    elif score >= 50:
        grade, grade_text = "C", "보통"
    elif score >= 45:
        grade, grade_text = "C-", "보통 이하"
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
# 9) Fallback용 상세 분석 텍스트 생성 (v8 - 자연어 개선)
# ============================================================
def build_analysis_text(
    raw: dict,
    difficulty_level: str,
    duration_min: int,
    item_count: int,
    total_time_sec: int,
) -> str:
    """
    규칙 기반 상세 분석 텍스트 생성 (LLM 호출 없음)
    v8: 자연어로 더 상세하고 친근하게 설명
    """

    health_info = interpret_health_data(raw)
    score_info = health_info["health_score"]
    sleep_info = health_info["sleep"]
    activity_info = health_info["activity"]
    hr_info = health_info["heart_rate"]
    exercise_rec = health_info["exercise_recommendation"]

    lines = []

    # ─────────────────────────────────────────
    # 1) 건강 점수 자연어 설명
    # ─────────────────────────────────────────
    score = score_info["score"]
    grade = score_info["grade"]
    grade_text = score_info["grade_text"]
    factors = score_info.get("factors", [])

    lines.append(f"📊 건강 점수: {score}점 ({grade}등급 - {grade_text})")

    # 점수 산정 근거를 자연어로 설명
    if factors:
        positive_factors = [f for f in factors if "+" in f]
        negative_factors = [f for f in factors if "-" in f]

        if positive_factors:
            lines.append(
                f"   ✅ 좋은 점: {', '.join([f.split('(')[0].strip() for f in positive_factors])}"
            )
        if negative_factors:
            lines.append(
                f"   ⚠️ 개선 필요: {', '.join([f.split('(')[0].strip() for f in negative_factors])}"
            )

    # ─────────────────────────────────────────
    # 2) 측정 데이터 자연어 요약
    # ─────────────────────────────────────────
    lines.append("")
    lines.append("📋 오늘의 건강 데이터:")

    # 수면
    sleep_hr = raw.get("sleep_hr", 0)
    sleep_min = raw.get("sleep_min", 0)
    if sleep_hr > 0:
        sleep_status = sleep_info.get("level", "")
        lines.append(
            f"   • 수면: {sleep_hr:.1f}시간 ({int(sleep_min)}분) - {sleep_status}"
        )
        lines.append(f"     → {sleep_info.get('recommendation', '')}")

    # 활동량
    steps = raw.get("steps", 0)
    distance_km = raw.get("distance_km", 0)
    if steps > 0:
        activity_level = activity_info.get("activity_level", "")
        level_kr = {
            "sedentary": "매우 낮음",
            "low": "낮음",
            "moderate": "보통",
            "active": "활발",
            "very_active": "매우 활발",
        }.get(activity_level, activity_level)

        lines.append(f"   • 걸음수: {steps:,}보 - 활동량 {level_kr}")
        if distance_km > 0:
            lines.append(f"   • 이동거리: {distance_km:.2f}km")
        lines.append(f"     → {activity_info.get('recommendation', '')}")

    # 심박수
    resting_hr = raw.get("resting_heart_rate", 0)
    avg_hr = raw.get("heart_rate", 0)
    if resting_hr > 0 or avg_hr > 0:
        hr_msg = hr_info.get("message", "")
        if resting_hr > 0:
            lines.append(f"   • 휴식기 심박수: {resting_hr}bpm")
        if avg_hr > 0:
            lines.append(f"   • 평균 심박수: {avg_hr}bpm")
        if hr_msg:
            lines.append(f"     → {hr_msg}")

    # 칼로리
    total_cal = raw.get("total_calories", 0)
    active_cal = raw.get("active_calories", 0)
    if total_cal > 0:
        lines.append(f"   • 총 소모 칼로리: {int(total_cal)}kcal")
    if active_cal > 0:
        lines.append(f"   • 활동 칼로리: {int(active_cal)}kcal")

    # ─────────────────────────────────────────
    # 3) 운동 권장 강도 + 상세 이유
    # ─────────────────────────────────────────
    lines.append("")
    rec_level = exercise_rec.get("recommended_level", difficulty_level)
    met_range = exercise_rec.get("met_range", "")
    reasons = exercise_rec.get("reasons", [])

    level_emoji = {"상": "🔥", "중": "💪", "하": "🌱"}.get(rec_level, "💪")
    level_desc = {
        "상": "고강도 운동이 가능한 컨디션입니다",
        "중": "중강도 운동으로 체력을 키워보세요",
        "하": "무리하지 않는 저강도 운동을 권장합니다",
    }.get(rec_level, "")

    lines.append(f"{level_emoji} 권장 운동 강도: {rec_level} ({met_range})")
    lines.append(f"   {level_desc}")

    if reasons:
        lines.append("")
        lines.append("   📌 강도 결정 이유:")
        for reason in reasons[:3]:
            lines.append(f"      • {reason}")

    # ─────────────────────────────────────────
    # 4) 운동 구성 설명
    # ─────────────────────────────────────────
    lines.append("")

    difficulty_detail = {
        "하": "관절에 무리가 없고 부상 위험이 낮은 저강도 운동으로 구성했습니다. 천천히 몸을 움직이며 운동 습관을 만들어보세요.",
        "중": "적당한 강도로 칼로리 소모와 체력 향상을 동시에 노릴 수 있는 운동들입니다. 꾸준히 하면 확실한 효과를 볼 수 있어요.",
        "상": "최대 효과를 위한 고강도 운동입니다. 충분한 워밍업 후 진행하고, 무리가 되면 휴식을 취하세요.",
    }

    lines.append(f"🏃 오늘의 운동 프로그램:")
    lines.append(f"   {difficulty_detail.get(difficulty_level, '')}")
    lines.append(f"   → 총 {item_count}개 운동, 약 {total_time_sec // 60}분 소요")

    # ─────────────────────────────────────────
    # 5) 안전 주의사항
    # ─────────────────────────────────────────
    if rec_level == "하" or score < 55:
        lines.append("")
        lines.append("⚠️ 주의사항:")
        lines.append("   • 운동 중 어지러움이나 통증이 있으면 즉시 중단하세요")
        lines.append("   • 충분한 수분을 섭취하며 진행하세요")
        if sleep_hr > 0 and sleep_hr < 6:
            lines.append("   • 수면이 부족하니 무리하지 마세요")

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
            summary_parts.append(f"수면 {sleep:.1f}시간")
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
