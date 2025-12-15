from fastapi import APIRouter, UploadFile, File

router = APIRouter(
    tags=["Video"]
)

@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    # 1) 업로드 받은 파일 읽기
    video_bytes = await file.read()

    # 2) (임시) AI 서버 없으므로 분석 없이 업로드 성공만 응답
    return {
        "filename": file.filename,
        "status": "업로드 성공! AI 분석은 아직 연결되지 않았습니다."
    }
