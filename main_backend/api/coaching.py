# app/api/coaching.py
"""
코칭 API 라우터
----------------------------------------
- POST /api/v1/coaching/start
- POST /api/v1/coaching/next
- POST /api/v1/coaching/finish

FastAPI sync 방식 + psycopg2 기반
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.coaching_service import start_coaching, next_step, finish_coaching

router = APIRouter(prefix="/api/v1/coaching", tags=["coaching"])


class StartReq(BaseModel):
    user_id: str
    routine_id: str


@router.post("/start")
def api_start(req: StartReq):
    """코칭 세션 시작"""
    return start_coaching(req.user_id, req.routine_id)


class NextReq(BaseModel):
    session_id: str


@router.post("/next")
def api_next(req: NextReq):
    """다음 세트·다음 운동 진행"""
    result = next_step(req.session_id)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


class FinishReq(BaseModel):
    session_id: str


@router.post("/finish")
def api_finish(req: FinishReq):
    """코칭 종료"""
    return finish_coaching(req.session_id)
