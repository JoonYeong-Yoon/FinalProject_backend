from fastapi import APIRouter, Depends

from db.database import get_db
from services.users.auth import get_current_user
from controllers.users.subscriptions.subscription_controller import start_subscription, cancel_subscription
from core.users.response import success, error
from core.users.permissions import require_scopes

router = APIRouter(tags=["subscriptions"])


@router.post("/start", dependencies=[Depends(require_scopes(["users:read"]))])
def start(current_user=Depends(get_current_user), db=Depends(get_db)):
    try:
        result = start_subscription(current_user["email"], db)
        return success({"message": "구독을 시작했습니다.", **result})
    except LookupError:
        return error("사용자를 찾을 수 없습니다.", 404, "USER_NOT_FOUND")
    except ValueError:
        return error("잘못된 요청입니다.", 400, "INVALID_EMAIL")
    except Exception:
        return error("구독 시작 실패", 500, "SUBSCRIPTION_START_FAILED")


@router.post("/cancel", dependencies=[Depends(require_scopes(["users:read"]))])
def cancel(current_user=Depends(get_current_user), db=Depends(get_db)):
    try:
        result = cancel_subscription(current_user["email"], db)
        return success({"message": "구독이 취소되었습니다.", **result})
    except LookupError:
        return error("사용자를 찾을 수 없습니다.", 404, "USER_NOT_FOUND")
    except ValueError:
        return error("잘못된 요청입니다.", 400, "INVALID_EMAIL")
    except Exception:
        return error("구독 취소 실패", 500, "SUBSCRIPTION_CANCEL_FAILED")
