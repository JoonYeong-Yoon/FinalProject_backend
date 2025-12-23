# app/api/coaching.py
"""
코칭 API 라우터
----------------------------------------
- POST /api/v1/coaching/start
- POST /api/v1/coaching/next
- POST /api/v1/coaching/finish
- POST /api/v1/coaching/cancel

FastAPI sync 방식 + psycopg2 기반
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from services.coaching_service import (start_coaching_session, next_step, 
                                       cancel_coaching_session, finish_coaching_session)
from config.settings import settings

router = APIRouter(prefix="/api/v1/coaching", tags=["coaching"])

class StartReq(BaseModel):
    # user_id: str
    ai_routine_id: str

class NextReq(BaseModel):
    coaching_session_id: str

class CancelReq(BaseModel):
    coaching_session_id: str
    cancellation_reason: str
    injury_area: str | None = None

class FinishReq(BaseModel):
    coaching_session_id: str

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/web/users/login")

@router.post("/start")
def start(
    req: StartReq,
    token: str = Depends(oauth2_scheme)):

    try:
        return start_coaching_session(
            # user_id=req.user_id,
            ai_routine_id=req.ai_routine_id, 
            token = token 
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/next")
def next_exercise(req: NextReq):
    try:
        return next_step(req.coaching_session_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/cancel")
def cancel(req: CancelReq):
    try:
        return cancel_coaching_session(
            coaching_session_id=req.coaching_session_id,
            cancellation_reason=req.cancellation_reason,
            injury_area=req.injury_area
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/finish")
def finish(req: FinishReq):
    try:
        return finish_coaching_session(req.coaching_session_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


