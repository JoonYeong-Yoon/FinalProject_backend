from fastapi import APIRouter, Depends, Body
from sqlalchemy.engine import Connection
from sqlalchemy import text

from db.database import get_db
from core.users.response import success, error
from core.users.permissions import require_scopes

LOGS_TABLE = "admin_logs"

router = APIRouter(tags=["admin logs"])


@router.get("/logs", dependencies=[Depends(require_scopes(["admin"]))])
def get_logs(db: Connection = Depends(get_db)):
    try:
        rows = db.execute(
            text(f"""
                SELECT * FROM {LOGS_TABLE}
                ORDER BY timestamp DESC
            """)
        ).mappings().all()

        return success([dict(row) for row in rows])
    except Exception:
        return error("로그 조회 실패", 500, "LOG_FETCH_FAILED")


@router.post("/logs", dependencies=[Depends(require_scopes(["admin"]))])
def create_log(data: dict = Body(...), db: Connection = Depends(get_db)):
    try:
        query = text(f"""
            INSERT INTO {LOGS_TABLE}
            (admin_email, action, target_user_id, target_user_email, timestamp)
            VALUES (:admin_email, :action, :target_user_id, :target_user_email, NOW())
        """)
        db.execute(query, data)
        db.commit()
        return success({"message": "log created"})
    except Exception:
        return error("로그 생성 실패", 500, "LOG_CREATE_FAILED")
