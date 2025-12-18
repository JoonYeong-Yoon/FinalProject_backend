from fastapi import APIRouter, UploadFile, File, Query
from app.service.file_upload_service import FileUploadService

router = APIRouter(prefix="/api/file", tags=["File Upload"])
service = FileUploadService()

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user_id: str | None = Query(None),
    difficulty: str = Query("중"),
    duration: int = Query(30),
):
    return await service.process_file(
        file=file,
        user_id=user_id,
        difficulty=difficulty,
        duration=duration
    )