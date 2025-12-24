"""
App API Router - 앱에서 업로드한 데이터 조회용 API
"""

from fastapi import APIRouter, Query, HTTPException
from app.core.vector_store import collection
import json

router = APIRouter(prefix="/api/app", tags=["app"])


@router.get("/latest")
def get_latest_app_data(
    user_id: str = Query(..., description="사용자 ID (이메일)"),
    watch_type: str = Query("galaxy", description="워치 타입: galaxy 또는 apple"),
):
    """
    앱에서 업로드한 최신 raw_json 데이터 조회
    
    웹 페이지에서 "서버에서 데이터 전송" 버튼 클릭 시 호출
    
    Parameters:
    - user_id: 사용자 ID (이메일)
    - watch_type: 워치 타입 (galaxy/apple)
    
    Returns:
    - raw_json: 앱에서 업로드한 건강 데이터
    - date: 데이터 날짜
    - source: 데이터 출처
    """
    print(f"[INFO] 앱 데이터 조회 요청: user_id={user_id}, watch_type={watch_type}")

    try:
        # 1. 해당 사용자의 모든 데이터 조회
        result = collection.get(where={"user_id": user_id})

        if not result or not result["metadatas"]:
            raise HTTPException(
                status_code=404,
                detail="업로드된 데이터가 없습니다. 먼저 스마트폰 앱에서 데이터를 전송해주세요.",
            )

        metadatas = result["metadatas"]
        
        # 2. 플랫폼 필터링 (galaxy → samsung, apple → apple)
        platform_filter = "samsung" if watch_type == "galaxy" else "apple"
        
        # 앱에서 업로드한 데이터만 필터링 (api_samsung, api_apple)
        filtered_data = []
        for meta in metadatas:
            source = meta.get("source", "")
            platform = meta.get("platform", "")
            
            # api_samsung 또는 api_apple 소스만 선택
            if f"api_{platform_filter}" in source or platform == platform_filter:
                filtered_data.append(meta)
        
        # 필터링된 데이터가 없으면 전체 데이터에서 최신 선택
        if not filtered_data:
            print(f"[WARN] {platform_filter} 플랫폼 데이터 없음, 전체 데이터에서 최신 선택")
            filtered_data = metadatas

        # 3. 날짜 기준 최신순 정렬
        sorted_data = sorted(
            filtered_data, 
            key=lambda x: x.get("date", ""), 
            reverse=True
        )

        if not sorted_data:
            raise HTTPException(
                status_code=404,
                detail="해당 조건의 데이터가 없습니다.",
            )

        # 4. 최신 데이터 추출
        latest_meta = sorted_data[0]
        date = latest_meta.get("date", "")
        source = latest_meta.get("source", "unknown")
        platform = latest_meta.get("platform", "unknown")

        print(f"[INFO] 최신 데이터 - 날짜: {date}, 출처: {source}, 플랫폼: {platform}")

        # 5. summary_json에서 raw 데이터 파싱
        summary_json = latest_meta.get("summary_json", "{}")
        try:
            summary_dict = json.loads(summary_json)
        except json.JSONDecodeError:
            summary_dict = {}

        raw_data = summary_dict.get("raw", {})
        summary_text = summary_dict.get("summary_text", "")

        if not raw_data:
            raise HTTPException(
                status_code=400,
                detail="건강 데이터가 비어있습니다.",
            )

        print(f"[SUCCESS] 앱 데이터 조회 완료 - 키: {list(raw_data.keys())[:5]}...")

        return {
            "success": True,
            "user_id": user_id,
            "date": date,
            "source": source,
            "platform": platform,
            "watch_type": watch_type,
            "raw_json": raw_data,
            "summary_text": summary_text,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] 앱 데이터 조회 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"데이터 조회 중 오류 발생: {str(e)}",
        )


@router.get("/history")
def get_app_history(
    user_id: str = Query(..., description="사용자 ID (이메일)"),
    watch_type: str = Query(None, description="워치 타입 필터 (선택)"),
    limit: int = Query(10, description="최대 조회 개수"),
):
    """
    앱에서 업로드한 데이터 히스토리 조회
    
    Parameters:
    - user_id: 사용자 ID
    - watch_type: 워치 타입 필터 (선택)
    - limit: 최대 조회 개수
    
    Returns:
    - data: 날짜별 데이터 목록
    """
    print(f"[INFO] 앱 히스토리 조회: user_id={user_id}, watch_type={watch_type}, limit={limit}")

    try:
        result = collection.get(where={"user_id": user_id})

        if not result or not result["metadatas"]:
            return {
                "success": True,
                "user_id": user_id,
                "count": 0,
                "data": [],
            }

        metadatas = result["metadatas"]
        
        # 플랫폼 필터링 (선택적)
        if watch_type:
            platform_filter = "samsung" if watch_type == "galaxy" else "apple"
            metadatas = [
                m for m in metadatas 
                if platform_filter in m.get("source", "") or m.get("platform", "") == platform_filter
            ]

        # 날짜 기준 최신순 정렬
        sorted_data = sorted(
            metadatas, 
            key=lambda x: x.get("date", ""), 
            reverse=True
        )[:limit]

        history = []
        for meta in sorted_data:
            summary_json = meta.get("summary_json", "{}")
            try:
                summary_dict = json.loads(summary_json)
            except:
                summary_dict = {}

            raw_data = summary_dict.get("raw", {})

            history.append({
                "date": meta.get("date", ""),
                "source": meta.get("source", "unknown"),
                "platform": meta.get("platform", "unknown"),
                "health_score": meta.get("health_score", 0),
                "has_data": bool(raw_data),
                "data_keys": list(raw_data.keys()) if raw_data else [],
            })

        print(f"[SUCCESS] 히스토리 조회 완료 - {len(history)}개")

        return {
            "success": True,
            "user_id": user_id,
            "count": len(history),
            "data": history,
        }

    except Exception as e:
        print(f"[ERROR] 히스토리 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"히스토리 조회 중 오류 발생: {str(e)}",
        )