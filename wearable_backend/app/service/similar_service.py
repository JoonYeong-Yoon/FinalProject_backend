from fastapi import HTTPException
from app.core.vector_store import search_similar_summaries


class SimilarService:
    """
    Summary + user_id를 기반으로 VectorDB에서 유사한 과거 summary 검색.
    similar_api.py에서는 이 서비스만 호출하면 된다.
    """

    @staticmethod
    def find_similar(summary: dict, user_id: str):
        """
        summary(dict)와 user_id를 받아서,
        VectorDB에서 유사 summary 검색을 수행한다.
        """

        # VectorDB query_dict 형식 맞추기
        query_dict = {
            "query": "summary comparison",
            "summary": summary
        }

        try:
            results = search_similar_summaries(
                query_dict=query_dict,
                user_id=user_id,
                top_k=3
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"유사도 검색 실패: {str(e)}")

        return {
            "message": "유사 요약 검색 성공",
            "results": results
        }
