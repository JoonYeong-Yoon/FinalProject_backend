def detect_platform(raw_json: dict) -> str:
    """
    삼성/애플 데이터를 key 존재 여부를 기반으로 자동 감지하는 함수.
    반환값: "samsung", "apple", "unknown"
    """

    # -------------------------
    # 삼성 전용 키 패턴
    # -------------------------
    samsung_keys = [
        "sleep",  # 삼성 sleep (분)
        "stepsCadence",  # 삼성 전용
        "totalCaloriesBurned",  # 삼성 소모 칼로리
    ]

    # 하나라도 존재하면 삼성으로 판정
    for k in samsung_keys:
        if k in raw_json:
            return "samsung"

    # -------------------------
    # 애플 전용 키 패턴
    # -------------------------
    apple_keys = [
        "sleepHours",  # 애플 수면 시간 (시간 단위)
        "activeEnergy",  # 애플 활동 칼로리
        "bodyFat",
        "leanBody",
        "walkingHeartRate",
        "hrv",
        "systolic",
        "diastolic",
        "glucose",
    ]

    for k in apple_keys:
        if k in raw_json:
            return "apple"

    # -------------------------
    # 둘 다 해당되지 않는 경우
    # -------------------------
    return "unknown"
