# FastAPI 관련 import
from fastapi import APIRouter, Depends, HTTPException

# DB 연결 및 서비스/모델 import
from db.database import get_db
from services.oauth2_service import get_current_user  # 현재 로그인 사용자 확인
from models.users_model import get_user_by_email, delete_user  # DB 조작 함수

# -----------------------------
# 사용자 관리 라우터 생성
# -----------------------------
router = APIRouter(tags=["manage"])  # Swagger UI에서 그룹화

# -----------------------------
# 회원 탈퇴 엔드포인트
# -----------------------------
@router.delete("/delete")
async def delete_account(current_user=Depends(get_current_user), db=Depends(get_db)):
    """
    현재 로그인한 사용자의 계정 삭제
    - current_user: JWT 토큰으로 인증된 사용자 정보
    - db: DB 연결 (Depends 사용)
    반환: 회원 탈퇴 완료 메시지
    """
    # 1. DB에서 사용자 정보 조회
    user = get_user_by_email(db, current_user["email"])
    if not user:  # 사용자 없으면 404 반환
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    # 2. 사용자 삭제
    delete_user(db, user["id"])

    # 3. 성공 메시지 반환
    return {"message": "회원 탈퇴가 완료되었습니다."}
