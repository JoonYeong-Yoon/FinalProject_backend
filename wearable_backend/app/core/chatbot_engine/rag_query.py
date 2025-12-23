"""
RAG Query - 개선 버전
- 기본: 최신 데이터
- 시간 표현 감지: 해당 기간 필터링
- 비교/패턴 키워드: 의미 유사도 검색
"""

import json
from datetime import datetime, timedelta
from app.core.vector_store import (
    search_similar_summaries,
    get_recent_summaries,
    get_summaries_by_date,
    get_summaries_by_date_range,
)


# ------------------------------------------------------------
# 1) Query 포맷팅
# ------------------------------------------------------------
def build_query_dict(message: str) -> dict:
    """
    사용자가 입력한 자연어 질문을 그대로 embedding 대상으로 사용.
    """
    return {"summary_text": message}


# ------------------------------------------------------------
# 2) 검색 결과 정리
# ------------------------------------------------------------
def _clean_results(similar_list: list) -> list:
    """검색 결과를 통일된 포맷으로 정리"""
    cleaned_results = []

    for item in similar_list:
        date_only = item.get("date")
        raw_data = item.get("raw") or {}

        cleaned_results.append(
            {
                "date": date_only,
                "similarity": item.get("similarity_distance"),
                "summary_text": item.get("summary_text"),
                "raw": raw_data,
                "source": item.get("source", "unknown"),
                "health_score": item.get("health_score"),
            }
        )

    return cleaned_results


# ------------------------------------------------------------
# 3) 최신 데이터 조회 (기본값)
# ------------------------------------------------------------
def query_latest_data(user_id: str, limit: int = 1) -> dict:
    """
    최신 날짜 데이터 조회 (기본 동작)

    Args:
        user_id: 사용자 ID
        limit: 가져올 개수 (기본 1 = 가장 최신)

    Returns:
        {"similar_days": [...], "count": int, "mode": "latest"}
    """
    results = get_recent_summaries(user_id, limit=limit)

    return {
        "similar_days": _clean_results(results),
        "count": len(results),
        "mode": "latest",
    }


# ------------------------------------------------------------
# 4) 특정 날짜 조회
# ------------------------------------------------------------
def query_by_date(user_id: str, target_date: str) -> dict:
    """
    특정 날짜 데이터 조회

    Args:
        user_id: 사용자 ID
        target_date: YYYY-MM-DD 형식

    Returns:
        {"similar_days": [...], "count": int, "mode": "specific_date"}
    """
    results = get_summaries_by_date(user_id, target_date)

    return {
        "similar_days": _clean_results(results),
        "count": len(results),
        "mode": "specific_date",
        "target_date": target_date,
    }


# ------------------------------------------------------------
# 5) 날짜 범위 조회
# ------------------------------------------------------------
def query_by_date_range(user_id: str, start_date: str, end_date: str) -> dict:
    """
    날짜 범위 데이터 조회

    Args:
        user_id: 사용자 ID
        start_date: 시작 날짜 (YYYY-MM-DD)
        end_date: 종료 날짜 (YYYY-MM-DD)

    Returns:
        {"similar_days": [...], "count": int, "mode": "date_range"}
    """
    results = get_summaries_by_date_range(user_id, start_date, end_date)

    return {
        "similar_days": _clean_results(results),
        "count": len(results),
        "mode": "date_range",
        "start_date": start_date,
        "end_date": end_date,
    }


# ------------------------------------------------------------
# 6) 의미 유사도 검색 (비교/패턴용)
# ------------------------------------------------------------
def query_by_similarity(message: str, user_id: str, top_k: int = 5) -> dict:
    """
    의미 유사도 기반 검색 (비교/패턴 분석용)

    Args:
        message: 사용자 질문
        user_id: 사용자 ID
        top_k: 가져올 개수

    Returns:
        {"similar_days": [...], "count": int, "mode": "similarity"}
    """
    query_dict = build_query_dict(message)
    result = search_similar_summaries(query_dict, user_id, top_k=top_k)

    similar_list = result.get("similar_days", [])

    return {
        "similar_days": _clean_results(similar_list),
        "count": len(similar_list),
        "mode": "similarity",
        "query": message,
    }


# ------------------------------------------------------------
# 7) 통합 쿼리 함수 (메인)
# ------------------------------------------------------------
def query_health_data(
    message: str, user_id: str, intent_result: dict = None, top_k: int = 3
) -> dict:
    """
    건강 데이터 조회 - 개선 버전

    동작 방식:
    1. 시간 표현 없고 비교/패턴 아님 → 최신 데이터
    2. 시간 표현 있음 → 해당 날짜/기간 필터링
    3. 비교/패턴 키워드 있음 → 의미 유사도 검색

    Args:
        message: 사용자 질문
        user_id: 사용자 ID
        intent_result: classify_intent() 결과 (optional)
        top_k: 가져올 개수

    Returns:
        {"similar_days": [...], "count": int, "mode": str}
    """
    # intent_result가 없으면 기본값 사용
    if intent_result is None:
        intent_result = {
            "intent": "health_query",
            "time_context": None,
            "use_similarity": False,
        }

    time_context = intent_result.get("time_context")
    use_similarity = intent_result.get("use_similarity", False)

    # Case 1: 비교/패턴 키워드 → 의미 유사도 검색
    if use_similarity:
        return query_by_similarity(message, user_id, top_k=top_k)

    # Case 2: 시간 표현 있음 → 날짜 필터링
    if time_context:
        if time_context["type"] == "specific":
            target_date = time_context["target_date"]
            result = query_by_date(user_id, target_date)

            # 해당 날짜에 데이터가 없으면 최신 데이터로 폴백
            if result["count"] == 0:
                print(f"[INFO] {target_date} 데이터 없음, 최신 데이터로 폴백")
                return query_latest_data(user_id, limit=1)

            return result

        elif time_context["type"] == "range":
            start_date = time_context["start_date"]
            end_date = time_context["end_date"]
            result = query_by_date_range(user_id, start_date, end_date)

            # 해당 기간에 데이터가 없으면 최신 데이터로 폴백
            if result["count"] == 0:
                print(f"[INFO] {start_date}~{end_date} 데이터 없음, 최신 데이터로 폴백")
                return query_latest_data(user_id, limit=top_k)

            return result

    # Case 3: 기본값 → 최신 데이터
    return query_latest_data(user_id, limit=1)


# ------------------------------------------------------------
# 8) 하위 호환용 (기존 코드 호환)
# ------------------------------------------------------------
def query_health_data_legacy(message: str, user_id: str, top_k: int = 3) -> dict:
    """
    기존 코드 호환용 - 항상 의미 유사도 검색
    (기존 동작 유지가 필요한 경우 사용)
    """
    return query_by_similarity(message, user_id, top_k=top_k)
