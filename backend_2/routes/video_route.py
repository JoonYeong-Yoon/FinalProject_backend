# routes/video_route.py

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4
import os
from sqlalchemy import text

from db.database import get_db

router = APIRouter(tags=["Video"])

UPLOAD_DIR = "uploads/exercise_videos"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_exercise_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    테스트용: 가장 최근 운동에 영상 자동 연결
    """

    # 1️⃣ 가장 최근 exercise 가져오기
    result = db.execute(text("""
        SELECT id FROM exercise
        ORDER BY id DESC
        LIMIT 1
    """)).mappings().first()

    if not result:
        raise HTTPException(status_code=404, detail="운동 데이터가 없습니다.")

    exercise_id = result["id"]

    # 2️⃣ 파일 저장
    ext = file.filename.split(".")[-1]
    filename = f"{uuid4()}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # 3️⃣ video_url 업데이트
    video_url = f"/{file_path.replace(os.sep, '/')}"
    db.execute(text("""
        UPDATE exercise
        SET video_url = :video_url
        WHERE id = :exercise_id
    """), {
        "video_url": video_url,
        "exercise_id": exercise_id
    })

    db.commit()

    return {
        "message": "운동 영상 업로드 완료 (자동 연결)",
        "exercise_id": exercise_id,
        "video_url": video_url
    }
