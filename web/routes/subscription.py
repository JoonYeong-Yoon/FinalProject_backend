from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from models.models import User
from web.services.oauth2 import get_current_user

router = APIRouter(tags=["Subscription"])  # ❗ prefix 제거


@router.post("/start")
def start_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user.is_subscribed = True
    db.commit()
    db.refresh(current_user)
    return {"message": "구독을 시작했습니다!"}


@router.post("/cancel")
def cancel_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user.is_subscribed = False
    db.commit()
    db.refresh(current_user)
    return {"message": "구독이 취소되었습니다!"}
