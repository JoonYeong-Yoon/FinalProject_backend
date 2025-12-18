"""
User API Router (수정 버전 - 날짜 기준 최신 데이터 조회)
"""

from fastapi import APIRouter, Query, HTTPException
from app.core.vector_store import collection, search_similar_summaries
from app.core.llm_analysis import run_llm_analysis
import json

router = APIRouter(prefix="/api/user", tags=["user"])


# ------------------------------------------------------------
# 1) 최신 분석 (수정: 날짜 기준 최신 데이터)
# ------------------------------------------------------------
@router.get("/latest-analysis")
def get_latest_analysis(
    user_id: str = Query(...), difficulty: str = Query("중"), duration: int = Query(30)
):
    """
    스마트폰 앱에서 업로드한 최신 데이터를 가져와서
    AI 분석 + 운동 추천까지 함께 반환

    웹 페이지에서 "분석 결과 가져오기" 버튼 클릭 시 호출

    ✅ 수정: 유사도가 아닌 날짜 기준으로 최신 데이터 조회
    """
    print(
        f"[INFO] 최신 분석 요청: user_id={user_id}, difficulty={difficulty}, duration={duration}분"
    )

    # ✅ 1. 날짜 기준으로 최신 데이터 가져오기
    try:
        result = collection.get(where={"user_id": user_id})

        if not result or not result["metadatas"]:
            raise HTTPException(
                404,
                "업로드된 데이터가 없습니다. 먼저 스마트폰 앱에서 데이터를 전송해주세요.",
            )

        # 날짜별로 정렬 (최신순)
        metadatas = result["metadatas"]
        sorted_data = sorted(metadatas, key=lambda x: x.get("date", ""), reverse=True)

        if not sorted_data:
            raise HTTPException(404, "데이터가 없습니다.")

        # 최신 데이터 추출
        latest_meta = sorted_data[0]
        date = latest_meta.get("date", "")

        print(f"[INFO] 최신 데이터 날짜: {date}")

        # summary_json 파싱
        summary_json = latest_meta.get("summary_json", "{}")
        try:
            summary_dict = json.loads(summary_json)
        except:
            summary_dict = {}

        raw_data = summary_dict.get("raw", {})
        summary_text = summary_dict.get("summary_text", "")

        if not raw_data:
            raise HTTPException(400, "건강 데이터가 비어있습니다.")

        # 데이터 개수 및 출처 정보 출력
        same_date_data = [m for m in sorted_data if m.get("date") == date]
        print(f"[INFO] 해당 날짜 데이터 개수: {len(same_date_data)}개")
        for idx, m in enumerate(same_date_data[:3], 1):
            source = m.get("source", "unknown")
            score = m.get("health_score", 0)
            print(f"[INFO] - 출처: {source}, 건강점수: {score}점")

        # 데이터 출처 분석
        sources = [m.get("source", "unknown") for m in same_date_data]
        if "api_samsung" in sources or "api_apple" in sources:
            print(f"[INFO] 분석 전략: API 최신 데이터 사용 (실시간)")
        elif "zip_samsung" in sources or "zip_apple" in sources:
            print(f"[WARN] 분석 전략: ZIP 업로드 데이터 사용 (과거 데이터)")
        else:
            print(f"[WARN] 분석 전략: 출처 불명 데이터 사용")

        print(f"[INFO] 주요 데이터 키: {list(raw_data.keys())[:10]}...")

        # 데이터 품질 검증
        has_sleep = raw_data.get("sleep_hr", 0) > 0 or raw_data.get("sleep_min", 0) > 0
        has_activity = (
            raw_data.get("steps", 0) > 0 or raw_data.get("distance_km", 0) > 0
        )

        if not has_sleep and not has_activity:
            print(f"[WARN] 데이터 품질: 수면/활동량 모두 0 (빈 데이터 가능성)")

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] 데이터 조회 실패: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(500, f"데이터 조회 중 오류 발생: {str(e)}")

    # 2. ⭐ summary 형식으로 재구성 (run_llm_analysis가 요구하는 형식)
    summary = {"created_at": date, "summary_text": summary_text, "raw": raw_data}

    # 3. AI 분석 + 운동 추천
    try:
        llm_result = run_llm_analysis(
            summary=summary,
            user_id=user_id,
            difficulty_level=difficulty,
            duration_min=duration,
        )

        print("[SUCCESS] AI 분석 완료")

        return {
            "success": True,
            "user_id": user_id,
            "date": date,
            "summary": {"summary_text": summary_text, "raw": raw_data},
            "analysis": llm_result.get("analysis", ""),
            "ai_recommended_routine": llm_result.get("ai_recommended_routine", {}),
            "detailed_health_report": llm_result.get("detailed_health_report", ""),
        }

    except Exception as e:
        print(f"[ERROR] AI 분석 중 오류: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(500, f"AI 분석 중 오류가 발생했습니다: {str(e)}")


# ------------------------------------------------------------
# 2) RAW-HISTORY 조회 (ZIP/앱에서 업로드된 모든 summary 조회)
# ------------------------------------------------------------
@router.get("/raw-history")
def get_raw_history(user_id: str = Query(...)):
    """
    사용자가 업로드한 summary/raw 전체 조회
    VectorDB에 저장된 summary_json을 파싱하여 반환
    """
    result = collection.get(where={"user_id": user_id})

    ids = result.get("ids", [])
    metas = result.get("metadatas", [])

    history = []
    for doc_id, meta in zip(ids, metas):
        # summary_json 파싱
        sj = meta.get("summary_json", "{}")
        try:
            parsed = json.loads(sj)
        except:
            parsed = {}

        raw = parsed.get("raw", {})
        summary_text = parsed.get("summary_text", "")

        history.append(
            {
                "doc_id": doc_id,
                "date": meta.get("date"),
                "source": meta.get("source", "unknown"),
                "platform": meta.get("platform", "unknown"),
                "health_score": meta.get("health_score", 0),
                "summary_text": summary_text,
                "raw": raw,
            }
        )

    return {"user_id": user_id, "count": len(history), "data": history}
