from fastapi import APIRouter, Query, HTTPException
from app.service.auto_upload_service import AutoUploadService
from pydantic import BaseModel

router = APIRouter(prefix="/api/auto", tags=["Auto Upload"])
service = AutoUploadService()


class UploadRequest(BaseModel):
    user_id: str
    date: str  # ✅ YYYY-MM-DD 형식
    raw_json: dict
    difficulty: str = "중"
    duration: int = 30


@router.post("/upload")
async def upload_json(payload: UploadRequest):
    """
    앱에서 날짜별 건강 데이터 업로드

    ✅ 수정: 날짜별로 개별 업로드
    - 앱에서 최근 7일치를 날짜별로 반복 호출
    - 각 날짜마다 벡터DB에 별도 저장

    📱 플랫폼 구분:
    - 삼성: useHealthConnect.ts → raw_json 전송 → platform="samsung"
    - 애플: HealthUploadModel.swift → raw_json 전송 → platform="apple"
    - VectorDB source: "api_samsung" or "api_apple"
    """
    print("=" * 60)
    print("📥 API 데이터 업로드 요청")
    print("=" * 60)
    print(f"User ID: {payload.user_id}")
    print(f"Date: {payload.date}")  # ✅ YYYY-MM-DD
    print(f"Difficulty: {payload.difficulty}")
    print(f"Duration: {payload.duration}분")
    print(f"Data keys: {list(payload.raw_json.keys())}")
    print("=" * 60)

    try:
        result = await service.process_json(
            json_data=payload.raw_json,
            user_id=payload.user_id,
            date=payload.date,  # ✅ 날짜 전달
            difficulty=payload.difficulty,
            duration=payload.duration,
        )
        print(f"✅ {payload.date} 데이터 처리 완료")
        return result

    except Exception as e:
        print(f"❌ {payload.date} 데이터 처리 실패: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
