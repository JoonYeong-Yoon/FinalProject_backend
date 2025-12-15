from fastapi import APIRouter, Depends
from sqlalchemy.engine import Connection

from db.database import get_db
from core.users.response import success, error
from core.users.permissions import require_scopes
from services.users.auth import get_current_user
from controllers.users.admin.admin_controller import (
    admin_get_users,
    admin_get_user,
    admin_delete_user,
    admin_update_role,
    admin_update_subscription
)

from models.users.schemas.admin import (
    AdminRoleUpdate,
    AdminSubscriptionUpdate
)

router = APIRouter(tags=["admin users"], dependencies=[Depends(get_current_user)])


@router.get("/users", dependencies=[Depends(require_scopes(["users:read"]))])
def admin_get_users(db: Connection = Depends(get_db)):
    try:
        return success(admin_get_users(db))
    except Exception:
        return error("사용자 조회 실패", 500, "USERS_FETCH_FAILED")


@router.get("/users/{user_id}", dependencies=[Depends(require_scopes(["users:read"]))])
def admin_get_user(user_id: str, db: Connection = Depends(get_db)):
    try:
        return success(admin_get_user(db, user_id))
    except LookupError:
        return error("사용자를 찾을 수 없습니다.", 404, "USER_NOT_FOUND")
    except Exception:
        return error("사용자 상세 조회 실패", 500, "USER_DETAIL_FETCH_FAILED")


@router.delete("/users/{user_id}", dependencies=[Depends(require_scopes(["users:write"]))])
def admin_delete_user(user_id: str, db: Connection = Depends(get_db)):
    try:
        admin_delete_user(db, user_id)
        return success({"message": "회원 정보가 삭제되었습니다."})
    except LookupError:
        return error("해당 회원이 존재하지 않습니다.", 404, "USER_NOT_FOUND")
    except Exception:
        return error("회원 삭제 실패", 500, "USER_DELETE_FAILED")


@router.patch("/users/{user_id}/role", dependencies=[Depends(require_scopes(["admin"]))])
def admin_update_role(user_id: str, body: AdminRoleUpdate, db: Connection = Depends(get_db)):
    try:
        result = admin_update_role(db, user_id, body.role)
        return success({"message": "권한이 변경되었습니다.", **result})
    except ValueError:
        return error("role 값은 admin 또는 user만 가능합니다.", 400, "INVALID_ROLE")
    except LookupError:
        return error("해당 유저를 찾을 수 없습니다.", 404, "USER_NOT_FOUND")
    except Exception:
        return error("권한 변경 실패", 500, "ROLE_UPDATE_FAILED")


@router.patch("/users/{user_id}/subscription", dependencies=[Depends(require_scopes(["subscription:manage"]))])
def admin_update_subscription(
    user_id: str,
    body: AdminSubscriptionUpdate,
    db: Connection = Depends(get_db),
):
    try:
        result = admin_update_subscription(db, user_id, body.is_subscribed)
        return success({"message": "구독 상태가 변경되었습니다.", **result})
    except LookupError:
        return error("사용자를 찾을 수 없습니다.", 404, "USER_NOT_FOUND")
    except Exception:
        return error("구독 상태 변경 실패", 500, "SUBSCRIPTION_UPDATE_FAILED")
