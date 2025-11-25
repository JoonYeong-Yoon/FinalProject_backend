# FastAPI 관련 import
from fastapi import APIRouter, UploadFile, File

# -----------------------------
# 비디오 업로드 라우터 생성
# -----------------------------
router = APIRouter(tags=["Video"])  # Swagger UI에서 그룹화

# -----------------------------
# 비디오 업로드 엔드포인트
# -----------------------------
@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """
    비디오 파일 업로드 처리
    - file: 클라이언트가 전송한 업로드 파일 (UploadFile)
    반환: 업로드 파일명 및 상태 메시지
    """
    # 1. 파일 내용 읽기
    video_bytes = await file.read()  # 실제 저장 또는 AI 분석 로직 연동 가능

    # 2. 성공 메시지 반환 (현재는 단순 확인용)
    return {
        "filename": file.filename,
        "status": "업로드 성공! (AI 분석 연동 예정)"
    }
