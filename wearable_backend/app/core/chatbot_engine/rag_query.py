import json
from app.core.vector_store import search_similar_summaries


# ------------------------------------------------------------
# 1) Query 포맷팅
# ------------------------------------------------------------
def build_query_dict(message: str) -> dict:
    """
    사용자가 입력한 자연어 질문을 그대로 embedding 대상으로 사용.
    """
    return {"summary_text": message}


# ------------------------------------------------------------
# 2) RAG 실행
# ------------------------------------------------------------
def query_health_data(message: str, user_id: str, top_k: int = 3) -> dict:
    """
    VectorDB에서 유사 health summary 검색 및 정리.
    """
    # 1) 쿼리 dictionary 생성
    query_dict = build_query_dict(message)

    # 2) VectorDB 검색 실행
    result = search_similar_summaries(query_dict, user_id, top_k=top_k)

    similar_list = result.get("similar_days", [])

    cleaned_results = []

    for item in similar_list:
        date_only = item.get("date")  # 이미 YYYY-MM-DD
        raw_data = item.get("raw") or {}

        cleaned_results.append(
            {
                "date": date_only,
                "similarity": item.get("similarity"),
                "summary_text": item.get("summary_text"),
                "raw": raw_data,
            }
        )

    return {
        "similar_days": cleaned_results,
        "count": len(cleaned_results),
    }
