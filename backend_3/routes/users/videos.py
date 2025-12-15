from fastapi import APIRouter, UploadFile, File
from core.users.response import success, error

router = APIRouter(tags=["videos"])


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    try:
        _ = await file.read()
        return success({
            "filename": file.filename,
            "status": "업로드 성공! (AI 분석 연동 예정)"
        })
    except Exception:
        return error("업로드 실패", 500, "VIDEO_UPLOAD_FAILED")
