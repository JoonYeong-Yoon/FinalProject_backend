# app/api/activity.py
"""
액티비티(영상 업로드) 라우터
- 업로드를 받아 DB에 PENDING 작업으로 등록하고, 백그라운드(또는 외부 워커)에서 처리하도록 설계
- 실시간 처리(스트리밍)는 이번 단계에서 제외
"""
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Form
from uuid import uuid4
from core.db import get_db_connection
from typing import Optional
from services.activity_service import enqueue_video_processing

router = APIRouter(prefix="/api/v1/activity", tags=["activity"])

@router.post("/upload")
async def upload_activity_video(background_tasks: BackgroundTasks, file: UploadFile = File(...), user_id: Optional[str] = Form(None)):
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")

    ext = file.filename.split(".")[-1]
    save_path = f"/tmp/{uuid4()}.{ext}"
    # 파일 저장
    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # DB에 activity_logs(PENDING) 생성
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO activity_logs (user_id, status) VALUES (%s, %s) RETURNING id;", (user_id, "PENDING"))
    activity_id = cur.fetchone()[0]
    conn.commit()
    conn.close()

    # 백그라운드 처리 큐에 등록 (서비스 레이어 구현)
    background_tasks.add_task(enqueue_video_processing, save_path, str(activity_id), user_id)

    return {"activity_id": str(activity_id), "status": "PENDING"}
