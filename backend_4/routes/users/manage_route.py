# FastAPI 관련 import
from fastapi import APIRouter, Depends, HTTPException

# DB 연결 및 서비스/모델 import
from db.database import get_db
from services.oauth2_service import get_current_user, admin_required  # 역할 기반 인증
from models.users_model import get_user_by_email, get_user_by_id, delete_user  # DB 조작 함수

# -----------------------------
# 사용자 관리 라우터 생성
# -----------------------------
router = APIRouter(tags=["manage"])  # Swagger UI에서 그룹화


# -----------------------------
# 1) 일반 사용자: 본인 계정 삭제
# -----------------------------
@router.delete("/delete")
async def delete_account(
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    현재 로그인한 사용자의 계정 삭제
    - user: 본인만 탈퇴 가능 (role과 관계 없음)
    """
    # DB에서 본인 정보 조회
    user = get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    # 삭제 실행
    delete_user(db, user["id"])

    return {"message": "회원 탈퇴가 완료되었습니다."}


# -----------------------------
# 2) 관리자 전용: 특정 사용자 삭제
# -----------------------------
@router.delete("/admin/delete/{target_user_id}")
async def admin_delete_user(
    target_user_id: str,
    current_user = Depends(admin_required),
    db = Depends(get_db)
):
    """
    관리자 전용: 특정 사용자 계정 삭제
    """
    # 삭제할 대상 조회
    target_user = get_user_by_id(db, target_user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="삭제할 사용자를 찾을 수 없습니다.")

    # 삭제 실행
    delete_user(db, target_user_id)

    return {
        "message": f"관리자가 사용자(id={target_user_id})를 삭제했습니다.",
        "admin": current_user["email"]
    }
