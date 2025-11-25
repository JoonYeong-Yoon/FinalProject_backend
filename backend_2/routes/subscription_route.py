# FastAPI 관련 import
from fastapi import APIRouter, Depends

# DB 연결 및 서비스/컨트롤러 import
from db.database import get_db
from services.oauth2_service import get_current_user  # JWT 인증 사용자 확인
from controllers.subscription_controller import start_subscription, cancel_subscription  # 구독 컨트롤러

# -----------------------------
# 구독 관련 라우터 생성
# -----------------------------
router = APIRouter(tags=["Subscription"])  # Swagger UI에서 그룹화

# -----------------------------
# 구독 시작 엔드포인트
# -----------------------------
@router.post("/start")
def start(current_user=Depends(get_current_user), db=Depends(get_db)):
    """
    현재 로그인한 사용자의 구독 시작
    - current_user: JWT 인증 사용자
    - db: DB 연결
    반환: 구독 시작 메시지
    """
    return start_subscription(current_user["email"], db)

# -----------------------------
# 구독 취소 엔드포인트
# -----------------------------
@router.post("/cancel")
def cancel(current_user=Depends(get_current_user), db=Depends(get_db)):
    """
    현재 로그인한 사용자의 구독 취소
    - current_user: JWT 인증 사용자
    - db: DB 연결
    반환: 구독 취소 메시지
    """
    return cancel_subscription(current_user["email"], db)
