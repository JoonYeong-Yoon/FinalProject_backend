"""
Intent Classifier - GPT Fallback 제거 버전
규칙 기반만 사용하여 LLM 호출 제거
"""

import time

# ================================================================
#  캐싱 (5분 TTL로 연장)
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
#  HEALTH KEYWORDS (확장)
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
#  ROUTINE KEYWORDS (확장)
# ================================================================
ROUTINE_EXPLICIT_KEYWORDS = [
    # 명확한 루틴 요청
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
    # 추가 패턴
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

# 문맥 기반 키워드: 단독으로는 ambiguous → 문장 패턴 분석 필요
ROUTINE_CONTEXT_KEYWORDS = [
    "운동 뭐",
    "운동할까",
    "오늘 운동",
    "뭐 운동",
    "workout",
]


# ================================================================
#  규칙 기반 분류 (확장)
# ================================================================
def _rule_based_intent(message: str):
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
#  메인 함수 (GPT fallback 제거!)
# ================================================================
def classify_intent(message: str) -> str:
    """
    Intent 분류 - 규칙 기반만 사용
    GPT fallback 제거로 LLM 호출 0회
    """
    # 캐시 확인
    cached = _cache_get(message)
    if cached:
        return cached

    # 규칙 기반 분류
    intent = _rule_based_intent(message)

    if intent:
        _cache_set(message, intent)
        return intent

    # ✅ GPT fallback 제거 - 매칭 안 되면 default_chat
    _cache_set(message, "default_chat")
    return "default_chat"
