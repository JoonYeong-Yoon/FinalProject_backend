def detect_platform(raw_json: dict) -> str:
    """
    삼성/애플 데이터를 key 존재 여부를 기반으로 자동 감지하는 함수.
    반환값: "samsung", "apple"

    ✅ 개선 사항:
    1. 삼성 키를 먼저 검사 (한국 사용자 다수)
    2. hrv, systolic, diastolic, glucose는 공통 키로 처리
    3. 애플 전용 키는 camelCase 패턴만 인식
    """

    # -------------------------
    # 삼성 전용 키 패턴 (먼저 검사 - 한국 사용자 다수)
    # -------------------------
    samsung_only_keys = [
        # 삼성 고유 키
        "sleep",  # 삼성 수면 (분 단위)
        "stepsCadence",  # 삼성 걸음 케이던스
        "totalCaloriesBurned",  # 삼성 총 소모 칼로리
        "calories",  # 삼성 활동 칼로리
        # snake_case 변형 (삼성에서 주로 사용)
        "steps_cadence",
        "total_calories_burned",
        "resting_heart_rate",
        "heart_rate",
        "sleep_min",  # 삼성 수면 (분)
        "sleep_hr",  # 삼성 수면 (시간)
        "active_calories",  # 삼성 활동 칼로리
        "total_calories",  # 삼성 총 칼로리
        "distance_km",  # 삼성 이동거리 (km)
        "body_fat",  # 삼성 체지방 (snake_case)
        "lean_body",  # 삼성 제지방 (snake_case)
        "exercise_min",  # 삼성 운동 시간 (분)
        "oxygen_saturation",  # 삼성 산소포화도
        "calories_intake",  # 삼성 섭취 칼로리
        "walking_heart_rate",  # 삼성 걷기 심박수
    ]

    for k in samsung_only_keys:
        if k in raw_json:
            return "samsung"

    # -------------------------
    # 애플 전용 키 패턴 (camelCase만 - 확실한 구분)
    # -------------------------
    apple_only_keys = [
        "sleepHours",  # 애플 수면 (시간 단위)
        "activeEnergy",  # 애플 활동 에너지
        "bodyFat",  # 애플 체지방 (camelCase)
        "leanBody",  # 애플 제지방 (camelCase)
        "walkingHeartRate",  # 애플 걷기 심박수 (camelCase)
        "basalEnergy",  # 애플 기초대사량
        "standHours",  # 애플 스탠드 시간
        "exerciseMinutes",  # 애플 운동 시간 (camelCase)
        "restingHeartRate",  # 애플 휴식 심박수 (camelCase)
        "heartRate",  # 애플 심박수 (camelCase)
    ]

    for k in apple_only_keys:
        if k in raw_json:
            return "apple"

    # -------------------------
    # 공통 키만 있는 경우 (삼성 우선)
    # -------------------------
    # hrv, systolic, diastolic, glucose는 양쪽 다 사용 → 삼성 우선
    common_keys = [
        "steps",
        "weight",
        "height",
        "bmi",
        "hrv",
        "systolic",
        "diastolic",
        "glucose",
        "flights",
    ]
    for k in common_keys:
        if k in raw_json:
            return "samsung"

    # -------------------------
    # 판단 불가 시 samsung 기본값
    # -------------------------
    return "samsung"
