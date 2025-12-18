"""
Health Data Preprocessing 모듈 (None 값 안전 처리 버전)

✅ 수정사항:
- None 값을 0으로 안전하게 변환
- JSON의 null → Python의 None 처리
- Infinity/NaN → null → None 처리
"""

from datetime import datetime, timezone, timedelta


def epoch_day_to_date_string(epoch_day: int) -> str:
    """
    Epoch Day Number → YYYY-MM-DD 변환

    Args:
        epoch_day: 1970-01-01부터의 일수

    Returns:
        YYYY-MM-DD 형식 문자열

    Examples:
        19992 → 2024-10-06
        20438 → 2025-12-17
    """
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    target_date = epoch + timedelta(days=epoch_day)
    return target_date.strftime("%Y-%m-%d")


def normalize_raw(raw_json: dict) -> dict:
    """
    ✅ None 값 안전 처리 추가

    JSON에서 null (Python의 None)이 올 수 있는 경우:
    - JavaScript에서 NaN/Infinity → JSON null
    - 빈 값 → null
    """
    platform = raw_json.get("platform", "samsung")

    # ✅ 안전한 값 추출 함수
    def safe_get(key, default=0):
        """None을 안전하게 처리"""
        value = raw_json.get(key, default)
        return value if value is not None else default

    # ---------------------------------------------------------
    # 1) 수면 시간 처리
    # ---------------------------------------------------------
    sleep_min = safe_get("sleep_min", 0)
    sleep_hr = safe_get("sleep_hr", 0)

    if sleep_min == 0 and sleep_hr > 0:
        sleep_min = sleep_hr * 60
    elif sleep_hr == 0 and sleep_min > 0:
        sleep_hr = sleep_min / 60

    # ---------------------------------------------------------
    # 2) 체중 처리
    # ---------------------------------------------------------
    weight = safe_get("weight", 0)

    # ---------------------------------------------------------
    # 3) 키 처리 (cm → m 변환)
    # ---------------------------------------------------------
    height_m = safe_get("height_m", 0)

    if height_m == 0:
        h = safe_get("height", 0)
        if h == 0:
            height_m = 0
        elif h < 3:
            height_m = h
        elif 30 <= h <= 250:
            height_m = h / 100
        else:
            height_m = h

    # ---------------------------------------------------------
    # 4) BMI 계산 (✅ None 안전 처리)
    # ---------------------------------------------------------
    bmi_value = raw_json.get("bmi")  # ✅ 기본값 없이 가져오기

    if bmi_value is not None and bmi_value > 0:
        # ✅ None이 아니고 0보다 큰 경우만 사용
        bmi = bmi_value
    elif weight > 0 and height_m > 0:
        # 직접 계산
        bmi = weight / (height_m**2)
    else:
        bmi = 0

    # ---------------------------------------------------------
    # 5) Distance 단위 통합
    # ---------------------------------------------------------
    distance_km = safe_get("distance_km", 0)
    if distance_km == 0:
        distance = safe_get("distance", 0)
        if distance > 0:
            distance_km = distance / 1000

    # ---------------------------------------------------------
    # 6) Calories 처리
    # ---------------------------------------------------------
    if platform == "samsung":
        active_cal = safe_get("active_calories", 0)
        total_cal = safe_get("total_calories", 0)
        calories_intake = 0
    else:
        active_cal = safe_get("activeEnergy", 0)
        total_cal = safe_get("total_calories", 0)
        calories_intake = safe_get("calories_intake", 0)

    # ---------------------------------------------------------
    # 7) 나머지 필드들 (✅ 모두 safe_get 사용)
    # ---------------------------------------------------------
    return {
        "sleep_min": sleep_min,
        "sleep_hr": sleep_hr,
        "weight": weight,
        "height_m": height_m,
        "bmi": bmi,
        "body_fat": safe_get("body_fat", 0),
        "lean_body": safe_get("lean_body", 0),
        "distance_km": distance_km,
        "steps": safe_get("steps", 0),
        "steps_cadence": safe_get("steps_cadence", 0),
        "exercise_min": safe_get("exercise_min", 0),
        "flights": safe_get("flights", 0),
        "active_calories": active_cal,
        "total_calories": total_cal,
        "calories_intake": calories_intake,
        "oxygen_saturation": safe_get("oxygen_saturation", 0),
        "heart_rate": safe_get("heart_rate", 0),
        "resting_heart_rate": safe_get("resting_heart_rate", 0),
        "walking_heart_rate": safe_get("walking_heart_rate", 0),
        "hrv": safe_get("hrv", 0),
        "systolic": safe_get("systolic", 0),
        "diastolic": safe_get("diastolic", 0),
        "glucose": safe_get("glucose", 0),
    }


def generate_summary_text(raw: dict) -> str:
    """요약 텍스트 생성 (0이 아닌 값만)"""
    parts = []

    if raw["sleep_hr"] > 0:
        parts.append(f"수면 {raw['sleep_hr']:.1f}시간({raw['sleep_min']:.0f}분)")

    if raw["bmi"] > 0:
        if raw["bmi"] < 18.5:
            bmi_status = "저체중"
        elif raw["bmi"] < 23:
            bmi_status = "정상"
        elif raw["bmi"] < 25:
            bmi_status = "과체중"
        else:
            bmi_status = "비만"
        parts.append(f"BMI {raw['bmi']:.1f}({bmi_status})")

    if raw["distance_km"] > 0:
        parts.append(f"이동거리 {raw['distance_km']:.2f}km")

    if raw["steps"] > 0:
        parts.append(f"걸음수 {raw['steps']:,}보")

    if raw["total_calories"] > 0:
        parts.append(f"총 소모 칼로리 {raw['total_calories']:.0f}kcal")

    if raw["heart_rate"] > 0:
        parts.append(f"심박수 {raw['heart_rate']:.0f}bpm")

    if raw["weight"] > 0:
        parts.append(f"체중 {raw['weight']:.0f}kg")

    if raw["height_m"] > 0:
        parts.append(f"키 {raw['height_m']:.2f}m")

    return " / ".join(parts) if parts else "데이터 없음"


def preprocess_health_json(
    raw_json: dict, date_int: int = None, platform: str = "unknown"
) -> dict:
    """
    건강 데이터 전처리

    Args:
        raw_json: 원본 건강 데이터
        date_int: 날짜 (YYYYMMDD 또는 Epoch Day)
        platform: 플랫폼 ('samsung', 'apple', 'unknown')

    Returns:
        전처리된 데이터 딕셔너리
    """
    # ✅ 플랫폼 정보 추가
    raw_json["platform"] = platform

    # 1. 날짜 처리
    if date_int:
        date_str = str(date_int)

        if len(date_str) == 8:
            # ✅ YYYYMMDD (8자리)
            year = date_str[:4]
            month = date_str[4:6]
            day = date_str[6:8]
            created_at = f"{year}-{month}-{day}T00:00:00+00:00"
            print(f"[INFO] 날짜 변환: {date_int} → {year}-{month}-{day}")

        elif len(date_str) <= 5:
            # ✅ Epoch Day (Samsung Health Connect ZIP)
            try:
                date_formatted = epoch_day_to_date_string(date_int)
                created_at = f"{date_formatted}T00:00:00+00:00"
                print(f"[INFO] Epoch Day 변환: {date_int} → {date_formatted}")
            except Exception as e:
                print(f"[ERROR] Epoch Day 변환 실패: {date_int}, 오류: {e}")
                created_at = datetime.now(timezone.utc).isoformat()
        else:
            print(f"[WARN] 잘못된 date_int 형식: {date_int}, 현재 시간 사용")
            created_at = datetime.now(timezone.utc).isoformat()
    else:
        # API 호출 - 현재 시간 사용
        created_at = datetime.now(timezone.utc).isoformat()

    # 2. 데이터 정규화 (✅ None 안전 처리 포함)
    try:
        raw_norm = normalize_raw(raw_json)
    except Exception as e:
        print(f"[ERROR] normalize_raw 실패: {e}")
        import traceback

        traceback.print_exc()
        raise

    # 3. 요약 텍스트 생성
    summary_text = generate_summary_text(raw_norm)

    # 4. 최종 결과
    return {
        "created_at": created_at,
        "summary_text": summary_text,
        "raw": raw_norm,
        "platform": platform,
    }
