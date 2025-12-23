import statistics
from typing import Dict
from datetime import datetime, timezone, timedelta


# =============================================================
# 내부 유틸
# =============================================================


def _mean(values):
    return statistics.mean(values) if values else 0


def _total(values):
    return sum(values) if values else 0


def _epoch_millis_to_local_date(epoch_millis: int) -> int:
    """
    epoch_millis → local_date (Epoch Day Number) 변환

    Args:
        epoch_millis: 밀리초 타임스탬프 (예: 1765983600000)

    Returns:
        Epoch Day Number (예: 20440)
    """
    if not epoch_millis:
        return None

    # 밀리초 → 초
    epoch_seconds = epoch_millis / 1000

    # UTC 기준 datetime
    dt = datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)

    # 한국 시간 (UTC+9) 적용
    kst = timezone(timedelta(hours=9))
    dt_kst = dt.astimezone(kst)

    # Epoch Day 계산 (1970-01-01부터의 일수)
    epoch = datetime(1970, 1, 1, tzinfo=kst)
    days = (dt_kst.date() - epoch.date()).days

    return days


def _init_day_bucket():
    """
    Samsung Health Connect ZIP 파싱용 bucket
    지정된 12개 항목만 수집
    """
    return {
        # Sleep
        "sleep": [],  # minutes
        # Body
        "weight": [],  # gram → kg
        "height": [],  # meter
        # Activity
        "steps": [],
        "distance": [],  # meter
        "steps_cadence": [],
        # Calories
        "total_calories": [],
        "active_calories": [],
        # Vitals
        "heart_rate": [],
        "resting_heart_rate": [],
        "oxygen_saturation": [],
    }


# =============================================================
# 날짜별 raw_json 생성 (Samsung Health Connect ZIP 전용)
# =============================================================


def parse_db_json_to_raw_data_by_day(db_json: dict) -> Dict[int, dict[str, float]]:
    """
    Health Connect SQLite DB(JSON 변환 결과)를 기반으로
    날짜별 raw_json을 생성한다.

    파싱 항목 (12개):
    - sleep, sleep_hr, weight, height
    - steps, distance, stepsCadence
    - totalCaloriesBurned, calories
    - heartRate, restingHeartRate, oxygenSaturation

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
    # 걸음 빈도 (step cadence)
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
    # 심박수 (Series 테이블에서 가져오기)
    # ---------------------------------------------------------
    for row in db_json.get("heart_rate_record_series_table", []):
        epoch_millis = row.get("epoch_millis")
        bpm = row.get("beats_per_minute", 0)

        if not epoch_millis or not bpm:
            continue

        date = _epoch_millis_to_local_date(epoch_millis)
        if date is None:
            continue

        add(date, "heart_rate", bpm)

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
    # 체중 (gram → kg)
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
    # 날짜별 raw_json 생성 (12개 항목)
    # ---------------------------------------------------------
    result_by_day = {}

    for date_key, d in grouped.items():
        sleep_min = _total(d["sleep"])

        result_by_day[date_key] = {
            # Sleep
            "sleep": sleep_min,
            "sleep_hr": sleep_min / 60 if sleep_min > 0 else 0,
            # Body
            "weight": _mean(d["weight"]),
            "height": _mean(d["height"]),
            # Activity
            "steps": _total(d["steps"]),
            "distance": _total(d["distance"]),
            "stepsCadence": _mean(d["steps_cadence"]),
            # Calories
            "totalCaloriesBurned": _total(d["total_calories"]),
            "calories": _total(d["active_calories"]),
            # Vitals
            "heartRate": _mean(d["heart_rate"]),
            "restingHeartRate": _mean(d["resting_heart_rate"]),
            "oxygenSaturation": _mean(d["oxygen_saturation"]),
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
