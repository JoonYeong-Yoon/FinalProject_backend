# FastAPI 관련 import
from fastapi import APIRouter, Depends, HTTPException, Body

# DB 연결 및 모델/컨트롤러 import
from db.database import get_db
from services.oauth2_service import get_current_user

from models.users_model import (
    get_user_by_email,
    update_basic_user,
    delete_user
)

from models.user_body_model import (
    get_body_info,
    update_body_info
)

from models.user_info_model import (
    get_user_info,
    update_user_info as update_info
)


# -----------------------------
# 사용자 프로필 라우터 생성
# -----------------------------
router = APIRouter(
    prefix="/web/users",     # 프론트와 매칭되는 prefix
    tags=["users"]
)


# =============================
# 🔵 내 정보 조회
# =============================
@router.get("/me")
async def get_my_info(
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    # 1) 기본 user 정보
    user = get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    user_id = user["id"]

    # 2) body_info
    body = get_body_info(db, user_id) or {}

    # 3) user_info
    info = get_user_info(db, user_id) or {}

    # 4) 날짜 처리
    created_at = user.get("created_at")
    if created_at:
        try:
            created_at = created_at.strftime("%Y-%m-%d")
        except:
            created_at = str(created_at)[:10]

    # 5) 프론트로 반환
    return {
        # 기본 user 정보
        "name": user.get("name"),
        "email": user.get("email"),
        "phone": user.get("phone"),
        "age": user.get("age"),
        "gender": user.get("gender"),
        "goal": user.get("goal"),
        "avatar": user.get("avatar"),

        # body_info
        "height": body.get("height_cm"),
        "weight": body.get("weight_kg"),
        "bmi": body.get("bmi"),

        # user_info
        "dailyTime": info.get("dailytime"),
        "weekly": info.get("weekly"),
        "activity": info.get("activity"),
        "targetPeriod": info.get("targetperiod"),
        "intro": info.get("intro"),
        "prefer": info.get("prefer") if info.get("prefer") else [],

        "created_at": created_at
    }


# =============================
# 🔵 내 정보 수정 (update)
# =============================
@router.put("/update")
async def update_user_all(
    current_user=Depends(get_current_user),
    db=Depends(get_db),
    body: dict = Body(...)
):
    user = get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    user_id = user["id"]

    # ----------------------------------------
    # 1) 기본 user 테이블 업데이트
    # ----------------------------------------
    basic_fields = {}
    for key in ["name", "email", "phone", "age", "gender", "goal", "avatar"]:
        if key in body:
            basic_fields[key] = body[key]

    if basic_fields:
        update_basic_user(db, user_id, basic_fields)

    # ----------------------------------------
    # 2) user_info 테이블 업데이트
    # ----------------------------------------
    info_fields = {}
    for key in ["dailyTime", "weekly", "activity", "targetPeriod", "intro", "prefer"]:
        if key in body:
            info_fields[key] = body[key]

    if info_fields:
        update_info(db, user_id, info_fields, insert_if_missing=True)

    # ----------------------------------------
    # 3) body_info 테이블 업데이트
    # ----------------------------------------
    body_fields = {}
    if "height" in body:
        body_fields["height_cm"] = body["height"]

    if "weight" in body:
        body_fields["weight_kg"] = body["weight"]

    # BMI 자동 계산
    if "height" in body and "weight" in body:
        h = body["height"]
        w = body["weight"]
        if h and w:
            body_fields["bmi"] = round(w / ((h / 100) ** 2), 1)

    if body_fields:
        update_body_info(db, user_id, body_fields, insert_if_missing=True)

    return {"message": "프로필 업데이트 완료"}


# =============================
# 🔵 계정 삭제
# =============================
@router.delete("/delete")
async def delete_my_account(
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    user = get_user_by_email(db, current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    delete_user(db, user["id"])
    return {"message": "계정 삭제 완료"}
