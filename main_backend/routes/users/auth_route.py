# ============================================
# 🔥 AUTH ROUTE (회원가입 / 로그인 / 내정보 / 수정)
# ============================================

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import text   # SQL 실행용

# DB
from db.database import get_db

# 컨트롤러
from controllers.user.register_controller import register_user
from controllers.user.login_controller import login_user

# JWT
from services.oauth2_service import create_access_token, get_current_user

# 모델
from models.schemas import UserCreate


# user_info / user_body_info 수정용 함수들
from models.user_info_model import update_user_info
from models.users_model import update_basic_user
from models.user_body_model import update_body_info


# ============================================
# 라우터 생성
# ============================================
router = APIRouter(tags=["auth"])



# ============================================
# 1) 회원가입
# ============================================
@router.post("/register")
async def register(user: UserCreate = Body(...), db: Session = Depends(get_db)):
    print("\n🟦 [AUTH] 회원가입 요청:", user.dict())

    res = register_user(user.dict(), db)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])

    return res



# ============================================
# 2) 로그인
# ============================================
@router.post("/login")
async def login(user: dict = Body(...), db: Session = Depends(get_db)):
    print("\n🟦 [AUTH] 로그인 요청:", user)

    res = login_user(user, db)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])

    token = create_access_token({
        "sub": str(res["id"]),
        "role": res["role"]
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "name": res["name"],
        "role": res["role"]
    }



# ============================================
# 3) 내 정보 조회
# ============================================
@router.get("/me")
def get_me(current_user=Depends(get_current_user)):
    print("🟦 [AUTH] /me 요청 →", current_user)
    return current_user



# ============================================
# 4) 🔥 프로필 전체 업데이트
# ============================================
@router.put("/update")
def update_profile(
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    print("\n🟦 [AUTH] 프로필 업데이트 요청:", data)
    uid = current_user["id"]
    # ----------------------------------------
    # 1) users 테이블 업데이트
    # ----------------------------------------
    user_fields = {}
    if "birth_date" in data:
        data["birthdate"] = data["birth_date"]

    for col in ["email", "name", "phone", "gender", "goal","birthdate"]:
        if col in data:
            user_fields[col] = data[col]

    # if "email" in data:
    #     user_fields["email"] = data["email"]

    if user_fields:
        print("🟩 users 업데이트:", user_fields)
        set_clause = ", ".join([f"{col} = :{col}" for col in user_fields.keys()])
        db.execute(
            text(f"""
                UPDATE public.users
                SET {set_clause}
                WHERE id = :id
            """),
            {**user_fields, "id": uid}
        )
        db.commit()

    # ----------------------------------------
    # 2) user_info 업데이트
    # ----------------------------------------
    info_fields = {}
    # for key in [
    #     "phone", "intro", "gender", "goal",
    #     "dailyTime", "weekly", "prefer", "pain",
    #     "activity", "targetPeriod"
    # ]:
    if "height" in data:
        data["height_cm"] = data["height"]
    if "weight" in data:
        data["weight_kg"] = data["weight"]
    for key in [
        "height_cm", "weight_kg"]:
        
        if key in data:
            if data[key]=="" or data[key] is None:
                data[key] = 0
            info_fields[key] = data[key]

    if info_fields:
        print("🟩 user_info 업데이트:", info_fields)
        # update_user_info(db, uid, info_fields, insert_if_missing=True)
        update_basic_user(db, uid, info_fields)

    # ----------------------------------------
    # 3) 🔥 user_body_info 업데이트 (프론트 기준!)
    # ----------------------------------------
    body_fields = {}

    if "height_cm" in data:
        body_fields["height_cm"] = data["height_cm"]

    if "weight_kg" in data:
        body_fields["weight_kg"] = data["weight_kg"]

    # BMI 자동 계산
    if "height_cm" in data and "weight_kg" in data:
        if (not data["height_cm"] is None)&(not data["weight_kg"] is None):
            h = data["height_cm"] / 100
            w = data["weight_kg"]
            if h!=0:
                body_fields["bmi"] = round(w / (h * h), 1)
            else:
                body_fields["bmi"] = 0
        else:
            pass
    for key in [
        "body_fat", "skeletal_muscle", "bmr", "visceral_fat_level","water"]:
        if key in data:
            body_fields[key] = data[key]
            
    if body_fields:
        print("🟩 user_body_info 업데이트:", body_fields)
        update_body_info(db, uid, body_fields, insert_if_missing=True)

    return {
        "message": "프로필 업데이트 완료",
        "success": True,
        "data":body_fields,
    }

