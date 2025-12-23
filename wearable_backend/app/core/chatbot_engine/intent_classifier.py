"""
Intent Classifier - 개선 버전
- 시간 표현 감지 추가
- 비교/패턴 키워드 감지 추가
- 규칙 기반만 사용 (LLM 호출 없음)
"""

import time
import re
from datetime import datetime, timedelta

# ================================================================
#  캐싱 (5분 TTL)
# ================================================================
_intent_cache = {}
CACHE_TTL = 300  # 60초 → 300초로 연장


def _cache_get(key):
    data = _intent_cache.get(key)
    if not data:
        return None
    intent, timestamp = data
    if time.time() - timestamp > CACHE_TTL:
        return None
    return intent


def _cache_set(key, intent):
    _intent_cache[key] = (intent, time.time())


# ================================================================
#  시간 표현 키워드 (NEW)
# ================================================================
TIME_KEYWORDS = {
    # 상대적 시간
    "오늘": 0,
    "어제": 1,
    "그제": 2,
    "그저께": 2,
    "엊그제": 2,
    "3일전": 3,
    "3일 전": 3,
    "일주일전": 7,
    "일주일 전": 7,
    "1주일전": 7,
    "1주일 전": 7,
    "지난주": 7,
    "저번주": 7,
    "2주전": 14,
    "2주 전": 14,
    "한달전": 30,
    "한달 전": 30,
    "1달전": 30,
    "1달 전": 30,
    "지난달": 30,
    "저번달": 30,
}

# 기간 표현 (범위)
TIME_RANGE_KEYWORDS = [
    "이번주",
    "이번 주",
    "금주",
    "이번달",
    "이번 달",
    "금월",
    "최근 3일",
    "최근 일주일",
    "최근 한달",
    "최근 7일",
    "최근 30일",
]


# ================================================================
#  비교/패턴 키워드 (NEW) - 의미 유사도 활용
# ================================================================
COMPARISON_KEYWORDS = [
    # 비교
    "비교",
    "비교해",
    "비교해줘",
    "대비",
    "versus",
    "vs",
    "차이",
    # 패턴/추이
    "패턴",
    "추이",
    "추세",
    "변화",
    "트렌드",
    "경향",
    # 조건 검색
    "언제",
    "며칠",
    "무슨 날",
    "어느 날",
    "가장 많이",
    "가장 적게",
    "제일 많이",
    "제일 적게",
    "최고",
    "최저",
    # 과거 회상
    "예전",
    "전에",
    "과거",
    "그때",
]

# ================================================================
#  HEALTH KEYWORDS
# ================================================================
HEALTH_KEYWORDS = [
    # 수면
    "수면",
    "잠",
    "sleep",
    "몇시간",
    "잤",
    # 신체
    "체중",
    "몸무게",
    "weight",
    "키",
    "신장",
    "height",
    "bmi",
    "체지방",
    "제지방",
    "lean body",
    # 활동 (데이터)
    "걸음",
    "보폭",
    "steps",
    "cadence",
    "이동거리",
    "distance",
    "운동시간",
    "활동시간",
    "계단",
    "flights",
    "얼마나 걸었",
    "몇 걸음",
    "걸음수",
    # 칼로리
    "칼로리",
    "active calorie",
    "열량",
    "섭취 칼로리",
    "소모",
    # 바이탈
    "심박",
    "맥박",
    "heart rate",
    "산소포화",
    "oxygen",
    "hrv",
    "혈압",
    "수축기",
    "이완기",
    "glucose",
    "혈당",
    # 상태 질문
    "내 상태",
    "컨디션",
    "건강 어때",
    "오늘 어때",
]

# ================================================================
#  ROUTINE KEYWORDS
# ================================================================
ROUTINE_EXPLICIT_KEYWORDS = [
    "운동 추천",
    "추천 운동",
    "운동 루틴",
    "루틴",
    "routine",
    "운동 알려줘",
    "운동 알려",
    "운동 해줘",
    "30분 운동",
    "20분 운동",
    "40분 운동",
    "10분 운동",
    "1시간 운동",
    "하체 루틴",
    "상체 루틴",
    "전신 루틴",
    "유산소 루틴",
    "코어 루틴",
    "홈트",
    "홈트레이닝",
    "운동 시작",
    "워밍업",
    "쿨다운",
    "스트레칭",
    "하체",
    "상체",
    "전신",
    "코어",
    "복근",
    "등",
    "가슴",
    "팔",
    "뭐 운동",
    "운동 뭐",
]

ROUTINE_CONTEXT_KEYWORDS = [
    "운동 뭐",
    "운동할까",
    "오늘 운동",
    "뭐 운동",
    "workout",
    "뭐 해",
    "뭐해",
    "운동하자",
]


# ================================================================
#  시간 표현 감지 함수 (NEW)
# ================================================================
def detect_time_expression(message: str) -> dict:
    """
    메시지에서 시간 표현을 감지하고 날짜 범위를 반환

    Returns:
        {
            "detected": True/False,
            "type": "specific" | "range" | None,
            "days_ago": int (specific일 경우),
            "start_date": str (range일 경우),
            "end_date": str (range일 경우),
            "keyword": str (감지된 키워드)
        }
    """
    msg = message.strip().lower()
    today = datetime.now().date()

    # 1) 특정 날짜 키워드 감지
    for keyword, days_ago in TIME_KEYWORDS.items():
        if keyword in msg:
            target_date = today - timedelta(days=days_ago)
            return {
                "detected": True,
                "type": "specific",
                "days_ago": days_ago,
                "target_date": target_date.strftime("%Y-%m-%d"),
                "keyword": keyword,
            }

    # 2) 기간 키워드 감지
    for keyword in TIME_RANGE_KEYWORDS:
        if keyword in msg:
            if "이번주" in keyword or "금주" in keyword:
                # 이번 주 월요일부터 오늘까지
                start = today - timedelta(days=today.weekday())
                end = today
            elif "이번달" in keyword or "금월" in keyword:
                # 이번 달 1일부터 오늘까지
                start = today.replace(day=1)
                end = today
            elif "최근 3일" in keyword:
                start = today - timedelta(days=3)
                end = today
            elif "최근 7일" in keyword or "최근 일주일" in keyword:
                start = today - timedelta(days=7)
                end = today
            elif "최근 30일" in keyword or "최근 한달" in keyword:
                start = today - timedelta(days=30)
                end = today
            else:
                start = today - timedelta(days=7)
                end = today

            return {
                "detected": True,
                "type": "range",
                "start_date": start.strftime("%Y-%m-%d"),
                "end_date": end.strftime("%Y-%m-%d"),
                "keyword": keyword,
            }

    # 3) 숫자 + 일/주/달 패턴 감지 (예: "3일 전", "2주 전")
    pattern = r"(\d+)\s*(일|주|달|개월)\s*(전|ago)"
    match = re.search(pattern, msg)
    if match:
        num = int(match.group(1))
        unit = match.group(2)

        if unit == "일":
            days = num
        elif unit == "주":
            days = num * 7
        elif unit in ["달", "개월"]:
            days = num * 30
        else:
            days = num

        target_date = today - timedelta(days=days)
        return {
            "detected": True,
            "type": "specific",
            "days_ago": days,
            "target_date": target_date.strftime("%Y-%m-%d"),
            "keyword": match.group(0),
        }

    return {"detected": False, "type": None}


# ================================================================
#  비교/패턴 키워드 감지 함수 (NEW)
# ================================================================
def detect_comparison_pattern(message: str) -> bool:
    """비교/패턴/조건 키워드가 있는지 감지"""
    msg = message.strip().lower()

    for keyword in COMPARISON_KEYWORDS:
        if keyword in msg:
            return True

    return False


# ================================================================
#  규칙 기반 분류
# ================================================================
def _rule_based_intent(message: str) -> str:
    msg = message.strip().lower()

    # (A) 명확한 루틴 요청
    for kw in ROUTINE_EXPLICIT_KEYWORDS:
        if kw in msg:
            return "routine_request"

    # (B) 문맥 기반 루틴 요청
    for kw in ROUTINE_CONTEXT_KEYWORDS:
        if kw in msg:
            return "routine_request"

    # (C) 건강 데이터 질문
    for kw in HEALTH_KEYWORDS:
        if kw in msg:
            return "health_query"

    # (D) 규칙 매칭 실패
    return None


# ================================================================
#  메인 함수 (개선!)
# ================================================================
def classify_intent(message: str) -> dict:
    """
    Intent 분류 - 개선 버전

    Returns:
        {
            "intent": "health_query" | "routine_request" | "default_chat",
            "time_context": { ... } | None,
            "use_similarity": True | False
        }
    """
    # 캐시 확인
    cached = _cache_get(message)
    if cached:
        return cached

    # 1) 시간 표현 감지
    time_context = detect_time_expression(message)

    # 2) 비교/패턴 키워드 감지
    use_similarity = detect_comparison_pattern(message)

    # 3) 기본 intent 분류
    base_intent = _rule_based_intent(message)

    if not base_intent:
        base_intent = "default_chat"

    result = {
        "intent": base_intent,
        "time_context": time_context if time_context["detected"] else None,
        "use_similarity": use_similarity,
    }

    _cache_set(message, result)
    return result


# ================================================================
#  하위 호환용 함수 (기존 코드와 호환)
# ================================================================
def classify_intent_simple(message: str) -> str:
    """기존 코드 호환용 - intent 문자열만 반환"""
    result = classify_intent(message)
    return result["intent"]
