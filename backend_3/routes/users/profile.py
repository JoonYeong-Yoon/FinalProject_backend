from fastapi import APIRouter, Depends, Body
from sqlalchemy.engine import Connection

from db.database import get_db
from services.users.auth import get_current_user
from core.users.response import success, error

from models.users.users import get_user_by_email, delete_user
from models.users.user_profile import get_profile_info

from controllers.users.profile.profile_controller import update_profile

from core.users.exceptions import NotFoundException

router = APIRouter(tags=["users"])


@router.get("/me")
async def get_my_profile(
    current_user=Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    try:
        user = get_user_by_email(db, current_user["email"])
        if not user:
            raise NotFoundException("사용자를 찾을 수 없습니다.")

        user_id = user["id"]
        body, info = get_profile_info(db, user_id)
        
        created_at = user.get("created_at")
        if created_at:
            try:
                created_at = created_at.strftime("%Y-%m-%d")
            except Exception:
                created_at = str(created_at)[:10]

        data = {
            "name": user.get("name"),
            "email": user.get("email"),
            "phone": user.get("phone"),
            "age": user.get("age"),
            "gender": user.get("gender"),
            "goal": user.get("goal"),
            "avatar": user.get("avatar"),

            "height": body.get("height_cm"),
            "weight": body.get("weight_kg"),
            "bmi": body.get("bmi"),

            "dailyTime": info.get("dailytime"),
            "weekly": info.get("weekly"),
            "activity": info.get("activity"),
            "targetPeriod": info.get("targetperiod"),
            "intro": info.get("intro"),
            "prefer": info.get("prefer") if info.get("prefer") else [],

            "created_at": created_at
        }

        return success(data)

    except NotFoundException as e:
        return error(e.detail["error"]["message"], 404, "USER_NOT_FOUND")
    except Exception:
        return error("내 정보 조회 실패", 500, "PROFILE_FETCH_FAILED")


@router.put("/me")
async def update_my_profile(
    current_user=Depends(get_current_user),
    db: Connection = Depends(get_db),
    body: dict = Body(...)
):
    try:
        result = update_profile(db, current_user["id"], body)
        return success(result)
    except LookupError:
        return error("사용자를 찾을 수 없습니다.", 404, "USER_NOT_FOUND")
    except ValueError as e:
        return error(str(e), 400, "INVALID_REQUEST")
    except Exception:
        return error("프로필 수정 실패", 500, "PROFILE_UPDATE_FAILED")


@router.delete("/me")
async def delete_my_account(
    current_user=Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    try:
        delete_user(db, current_user["id"])
        return success({"message": "회원 탈퇴가 완료되었습니다."})
    except LookupError:
        return error("사용자를 찾을 수 없습니다.", 404, "USER_NOT_FOUND")
    except Exception:
        return error("회원 탈퇴 실패", 500, "ACCOUNT_DELETE_FAILED")
