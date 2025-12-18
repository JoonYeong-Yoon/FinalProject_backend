import statistics
from typing import Dict


# =============================================================
# 내부 유틸
# =============================================================


def _mean(values):
    return statistics.mean(values) if values else 0


def _total(values):
    return sum(values) if values else 0


def _init_day_bucket():
    """
    정규화 이전 raw 수집용 bucket
    - 단위 혼재 허용
    - preprocess에서 통합 처리됨
    """
    return {
        # Sleep
        "sleep": [],  # minutes or hours (platform-specific)
        # Body
        "weight": [],  # kg or g
        "height": [],  # m or cm
        "body_fat": [],
        "lean_body": [],
        # Activity
        "steps": [],
        "distance": [],  # meter
        "steps_cadence": [],
        "exercise_time": [],  # minutes
        "flights": [],
        # Calories
        "active_calories": [],
        "total_calories": [],
        "calories_intake": [],
        # Vitals
        "heart_rate": [],
        "resting_heart_rate": [],
        "walking_heart_rate": [],
        "hrv": [],
        "oxygen_saturation": [],
        # Medical
        "systolic": [],
        "diastolic": [],
        "glucose": [],
    }


# =============================================================
# 1️⃣ 날짜별 raw_json 생성 (RAG / 확장용)
# =============================================================


def parse_db_json_to_raw_data_by_day(db_json: dict) -> Dict[int, dict[str, float]]:
    """
    Health Connect SQLite DB(JSON 변환 결과)를 기반으로
    날짜별 raw_json을 생성한다.

    return:
      {
        local_date(int): raw_json(dict),
        ...
      }
    """

    if not db_json:
        return {}

    # 날짜별 그룹핑
    grouped = {}

    def add(date_key, key, value):
        if date_key not in grouped:
            grouped[date_key] = _init_day_bucket()
        grouped[date_key][key].append(value)

    # ---------------------------------------------------------
    # 걸음수
    # ---------------------------------------------------------
    for row in db_json.get("steps_record_table", []):
        date = row.get("local_date")
        if date is None:
            continue
        add(date, "steps", row.get("count", 0))

    # ---------------------------------------------------------
    # 이동거리 (meter 단위)
    # ---------------------------------------------------------
    for row in db_json.get("distance_record_table", []):
        date = row.get("local_date")
        if date is None:
            continue
        add(date, "distance", row.get("distance", 0))

    # ---------------------------------------------------------
    # 걸음 빈도(step cadence)
    # ---------------------------------------------------------
    for row in db_json.get("steps_cadence_record_table", []):
        date = row.get("local_date")
        if date is None:
            continue

        samples = row.get("samples") or row.get("samples_list")
        if samples and isinstance(samples, list):
            add(date, "steps_cadence", _mean(samples))

    # ---------------------------------------------------------
    # 총 칼로리 (energy = millikalories)
    # ---------------------------------------------------------
    for row in db_json.get("total_calories_burned_record_table", []):
        date = row.get("local_date")
        if date is None:
            continue

        kcal = row.get("energy", 0) / 1000
        add(date, "total_calories", kcal)

    # ---------------------------------------------------------
    # 활동 칼로리
    # ---------------------------------------------------------
    for row in db_json.get("active_calories_burned_record_table", []):
        date = row.get("local_date")
        if date is None:
            continue

        kcal = row.get("energy", 0) / 1000
        add(date, "active_calories", kcal)

    # ---------------------------------------------------------
    # 심박수
    # ---------------------------------------------------------
    for row in db_json.get("heart_rate_record_table", []):
        date = row.get("local_date")
        if date is None:
            continue
        add(date, "heart_rate", row.get("value", 0))

    # ---------------------------------------------------------
    # 휴식기 심박수
    # ---------------------------------------------------------
    for row in db_json.get("resting_heart_rate_record_table", []):
        date = row.get("local_date")
        if date is None:
            continue
        add(date, "resting_heart_rate", row.get("value", 0))

    # ---------------------------------------------------------
    # 산소포화도 (%)
    # ---------------------------------------------------------
    for row in db_json.get("oxygen_saturation_record_table", []):
        date = row.get("local_date")
        if date is None:
            continue
        add(date, "oxygen_saturation", row.get("percentage", 0))
    # ---------------------------------------------------------
    # 체중 (gram)
    # ---------------------------------------------------------
    for row in db_json.get("weight_record_table", []):
        date = row.get("local_date")
        if date is None:
            continue

        w = row.get("weight", 0)
        if w > 0:
            w = w / 1000
        add(date, "weight", w)

    # ---------------------------------------------------------
    # 키 (meter)
    # ---------------------------------------------------------
    for row in db_json.get("height_record_table", []):
        date = row.get("local_date")
        if date is None:
            continue
        add(date, "height", row.get("height", 0))

    # ---------------------------------------------------------
    # 수면 (start~end → minutes)
    # ---------------------------------------------------------
    for row in db_json.get("sleep_session_record_table", []):
        date = row.get("local_date")
        s, e = row.get("start_time"), row.get("end_time")

        if date is None or not s or not e:
            continue

        minutes = (e - s) / 1000 / 60
        add(date, "sleep", minutes)

    # ---------------------------------------------------------
    # 날짜별 raw_json 생성
    # ---------------------------------------------------------
    result_by_day = {}

    for date_key, d in grouped.items():
        result_by_day[date_key] = {
            # Sleep
            "sleep": _total(d["sleep"]),
            # Body
            "weight": _mean(d["weight"]),
            "height": _mean(d["height"]),
            # Activity
            "distance": _total(d["distance"]),
            "steps": _total(d["steps"]),
            "stepsCadence": _mean(d["steps_cadence"]),
            # Calories
            "calories": _total(d["active_calories"]),
            "totalCaloriesBurned": _total(d["total_calories"]),
            # Vitals
            "oxygenSaturation": _mean(d["oxygen_saturation"]),
            "heartRate": _mean(d["heart_rate"]),
            "restingHeartRate": _mean(d["resting_heart_rate"]),
            # Not provided by Samsung ZIP
            "exerciseTime": 0,
            "flights": 0,
            "bodyFat": 0,
            "leanBody": 0,
            "walkingHeartRate": 0,
            "hrv": 0,
            "systolic": 0,
            "diastolic": 0,
            "glucose": 0,
        }

    return result_by_day


# ---------------------------------------------------------
# 최신 1일치 raw_json 반환 (기존 호환용)
# ---------------------------------------------------------
def parse_db_json_to_raw_data(db_json: dict) -> dict:
    """
    기존 호환 유지용 함수.
    최신 날짜의 raw_json 1개만 반환한다.
    """

    by_day = parse_db_json_to_raw_data_by_day(db_json)

    if not by_day:
        return {}

    latest_date = max(by_day.keys())
    return by_day[latest_date]
