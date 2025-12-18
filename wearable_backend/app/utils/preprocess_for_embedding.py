def summary_to_natural_text(summary: dict) -> str:
    """
    VectorDB embedding 최적화용 문장 생성
    normalize_raw() 결과(raw dict)를 기반으로
    하루의 건강 데이터를 의미 단위로 연결한 문맥 있는 문장으로 변환한다.

    ✅ 빈 문자열 방지: 데이터가 없어도 최소한의 텍스트 반환
    """

    raw = summary.get("raw", {})
    parts = []

    # ----------------------------------------
    # 1) 수면
    # ----------------------------------------
    if raw.get("sleep_min", 0) > 0:
        parts.append(
            f"오늘 수면 시간은 {raw['sleep_hr']}시간, 총 {raw['sleep_min']}분입니다."
        )

    # ----------------------------------------
    # 2) 활동 지표 (steps, distance, cadence 등)
    # ----------------------------------------
    activity = []

    if raw.get("steps", 0) > 0:
        activity.append(f"{raw['steps']:,}보를 걸었습니다")

    if raw.get("distance_km", 0) > 0:
        activity.append(f"이동거리는 {raw['distance_km']:.2f}km였습니다")

    if raw.get("steps_cadence", 0) > 0:
        activity.append(f"분당 걸음수는 {raw['steps_cadence']}보입니다")

    if raw.get("exercise_min", 0) > 0:
        activity.append(f"운동 시간은 {raw['exercise_min']}분입니다")

    if raw.get("flights", 0) > 0:
        activity.append(f"오른 계단 수는 {raw['flights']}층입니다")

    if activity:
        parts.append("오늘의 활동으로는 " + ", ".join(activity) + ".")

    # ----------------------------------------
    # 3) 칼로리 지표
    # ----------------------------------------
    calories = []

    if raw.get("active_calories", 0) > 0:
        calories.append(f"활동 칼로리는 {raw['active_calories']}kcal")

    if raw.get("total_calories", 0) > 0:
        calories.append(f"총 소모 칼로리는 {raw['total_calories']}kcal")

    if raw.get("calories_intake", 0) > 0:
        calories.append(f"섭취 칼로리는 {raw['calories_intake']}kcal")

    if calories:
        parts.append("칼로리 측면에서는 " + ", ".join(calories) + "입니다.")

    # ----------------------------------------
    # 4) 바이탈 지표
    # ----------------------------------------
    vitals = []

    if raw.get("heart_rate", 0) > 0:
        vitals.append(f"심박수는 {raw['heart_rate']}bpm")

    if raw.get("resting_heart_rate", 0) > 0:
        vitals.append(f"휴식기 심박수는 {raw['resting_heart_rate']}bpm")

    if raw.get("walking_heart_rate", 0) > 0:
        vitals.append(f"걷기 심박수는 {raw['walking_heart_rate']}bpm")

    if raw.get("oxygen_saturation", 0) > 0:
        vitals.append(f"산소포화도는 {raw['oxygen_saturation']}%")

    if raw.get("hrv", 0) > 0:
        vitals.append(f"심박변이도는 {raw['hrv']}ms")

    if raw.get("systolic", 0) > 0 and raw.get("diastolic", 0) > 0:
        vitals.append(f"혈압은 {raw['systolic']}/{raw['diastolic']}mmHg")

    if raw.get("glucose", 0) > 0:
        vitals.append(f"혈당은 {raw['glucose']}mg/dL")

    if vitals:
        parts.append("바이탈 지표는 " + ", ".join(vitals) + "입니다.")

    # ----------------------------------------
    # 5) 신체 정보 (weight, height, BMI)
    # ----------------------------------------
    profile = []

    if raw.get("weight", 0) > 0:
        profile.append(f"체중은 {raw['weight']}kg")

    if raw.get("height_m", 0) > 0:
        profile.append(f"키는 {raw['height_m']:.2f}m")

    if raw.get("bmi", 0) > 0:
        profile.append(f"BMI는 {raw['bmi']:.1f}")

    if raw.get("body_fat", 0) > 0:
        profile.append(f"체지방률은 {raw['body_fat']}%")

    if raw.get("lean_body", 0) > 0:
        profile.append(f"제지방량은 {raw['lean_body']}kg")

    if profile:
        parts.append("신체 정보는 " + ", ".join(profile) + "입니다.")

    # ----------------------------------------
    # 최종 문장 합성
    # ----------------------------------------
    result = " ".join(parts)

    # ✅ 빈 문자열 방지 (OpenAI API는 빈 문자열 거부)
    if not result or not result.strip():
        # created_at이 있으면 날짜 정보라도 포함
        created_at = summary.get("created_at", "")
        if created_at:
            date = created_at[:10]
            return f"날짜: {date}에 건강 데이터가 기록되었습니다."
        else:
            return "건강 데이터가 기록되었습니다."

    return result
