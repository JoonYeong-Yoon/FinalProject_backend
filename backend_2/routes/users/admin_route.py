# ============================================
# 🛠 관리자 전용 API (Admin Router)
# ============================================

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from db.database import get_db
from services.oauth2_service import admin_required
from models.users_model import USERS_TABLE


# ============================================
# 📌 요청 body 모델 (역할 변경)
# ============================================
class RoleUpdate(BaseModel):
    role: str    # "admin" 또는 "user"


# ============================================
# 📌 라우터 설정 (prefix 없음)
# ============================================
router = APIRouter(
    tags=["admin"]
)


# ============================================
# 📌 1) 전체 사용자 조회
# ============================================
@router.get("/users")
def get_all_users(
    db: Session = Depends(get_db),
    admin=Depends(admin_required)
):
    print("\n🟦 [ADMIN] 전체 사용자 조회 요청")

    rows = db.execute(text(f"SELECT * FROM {USERS_TABLE}")).mappings().all()
    print(f"🟩 [ADMIN] 조회된 사용자 수: {len(rows)}")

    return [dict(row) for row in rows]


# ============================================
# 📌 2) 특정 사용자 조회
# ============================================
@router.get("/users/{user_id}")
def get_user_detail(
    user_id: str,
    db: Session = Depends(get_db),
    admin=Depends(admin_required)
):
    print(f"\n🟦 [ADMIN] 특정 사용자 조회 요청 → ID: {user_id}")

    row = db.execute(
        text(f"SELECT * FROM {USERS_TABLE} WHERE id = :id"),
        {"id": user_id}
    ).mappings().first()

    print(f"🟩 [ADMIN] 조회 결과: {row}")

    if not row:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    return dict(row)


# ============================================
# 📌 3) 구독 상태 변경
# ============================================
@router.post("/users/{user_id}/subscription")
def admin_change_subscription(
    user_id: str,
    is_subscribed: bool,
    db: Session = Depends(get_db),
    admin=Depends(admin_required)
):
    print(f"\n🟦 [ADMIN] 구독 상태 변경 요청 → ID: {user_id}, 상태: {is_subscribed}")

    update_query = text(f"""
        UPDATE {USERS_TABLE}
        SET is_subscribed = :sub
        WHERE id = :id
    """)

    result = db.execute(update_query, {"sub": is_subscribed, "id": user_id})
    db.commit()

    print(f"🟩 [ADMIN] 구독 상태 변경 rowcount: {result.rowcount}")

    return {
        "message": f"구독을 {'활성화' if is_subscribed else '취소'}했습니다.",
        "user_id": user_id,
        "new_status": is_subscribed
    }


# ============================================
# 📌 4) 회원 삭제
# ============================================
@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin=Depends(admin_required)
):
    print(f"\n🟦 [ADMIN] 회원 삭제 요청 → ID: {user_id}")

    delete_query = text(f"DELETE FROM {USERS_TABLE} WHERE id = :id")
    result = db.execute(delete_query, {"id": user_id})
    db.commit()

    print(f"🟩 [ADMIN] 삭제 rowcount: {result.rowcount}")

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="해당 회원이 존재하지 않습니다.")

    return {
        "message": "회원 정보가 삭제되었습니다.",
        "user_id": user_id
    }


# ============================================
# 📌 5) 관리자 승급 / 강등
# ============================================
@router.patch("/users/{user_id}/role")
def promote_user(
    user_id: str,
    data: RoleUpdate,     
    db: Session = Depends(get_db),
    admin=Depends(admin_required)
):
    print(f"\n🟦 [ADMIN] 역할 변경 요청 → ID: {user_id}, 변경할 role: {data.role}")

    # ======================================
    # 🔥 문자열 role → boolean 맵핑 처리
    # DB의 role 컬럼 타입은 boolean 이므로 변환 필요
    # ======================================
    if data.role == "admin":
        mapped_role = True
    elif data.role == "user":
        mapped_role = False
    else:
        raise HTTPException(status_code=400, detail="role 값은 admin 또는 user만 가능합니다.")

    update_query = text(f"""
        UPDATE {USERS_TABLE}
        SET role = :role
        WHERE id = :id
    """)

    result = db.execute(update_query, {
        "role": mapped_role,
        "id": user_id
    })

    db.commit()

    print(f"🟩 [ADMIN] 역할 변경 rowcount: {result.rowcount}")

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="해당 유저를 찾을 수 없습니다.")

    return {
        "message": "권한이 변경되었습니다.",
        "user_id": user_id,
        "previous_role": data.role,
        "stored_value_in_db": mapped_role
    }
