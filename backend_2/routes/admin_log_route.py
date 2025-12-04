from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.database import get_db
from services.oauth2_service import admin_required

LOGS_TABLE = "admin_logs"

router = APIRouter(
    prefix="/admin/logs",
    tags=["admin logs"]
)

# ============================================
# 📌 로그 조회
#    GET /admin/logs
# ============================================
@router.get("/")
def get_logs(
    db: Session = Depends(get_db),
    admin = Depends(admin_required)
):
    rows = db.execute(text(f"""
        SELECT * FROM {LOGS_TABLE}
        ORDER BY timestamp DESC
    """)).mappings().all()

    return [dict(row) for row in rows]


# ============================================
# 📌 로그 저장
#    POST /admin/logs
# ============================================
@router.post("/")
def create_log(
    data: dict = Body(...),
    db: Session = Depends(get_db),
    admin = Depends(admin_required)
):
    query = text(f"""
        INSERT INTO {LOGS_TABLE}
        (admin_email, action, target_user_id, target_user_email, timestamp)
        VALUES (:admin_email, :action, :target_user_id, :target_user_email, NOW())
    """)

    db.execute(query, data)
    db.commit()

    return {"message": "log created", "data": data}
