from fastapi import APIRouter, Depends, Body
from sqlalchemy.engine import Connection

from db.database import get_db
from controllers.users.auth.register_controller import register_user
from controllers.users.auth.login_controller import login_user
from services.users.auth import get_current_user
from services.users.jwt import create_access_token
from models.users.schemas.user import UserCreate
from core.users.response import success, error

router = APIRouter(tags=["auth"])


@router.post("/register")
async def register(user: UserCreate = Body(...), db: Connection = Depends(get_db)):
    try:
        result = register_user(user.dict(), db)
        return success(result, 201)
    except ValueError:
        return error("이미 존재하는 이메일입니다.", 409, "EMAIL_ALREADY_EXISTS")
    except Exception:
        return error("회원가입 실패", 500, "REGISTER_FAILED")


@router.post("/login")
async def login(user: dict = Body(...), db: Connection = Depends(get_db)):
    try:
        result = login_user(user, db)
    except LookupError:
        return error("등록되지 않은 이메일입니다.", 404, "USER_NOT_FOUND")
    except ValueError:
        return error("비밀번호가 올바르지 않습니다.", 400, "INVALID_PASSWORD")
    except Exception:
        return error("로그인 실패", 500, "LOGIN_FAILED")

    token = create_access_token({
        "sub": str(result["id"]),
        "role": result["role"]
    })

    # (기존 응답 유지하되, 포맷 통일 원하면 success로 감싸도 됨)
    return {
        "access_token": token,
        "token_type": "bearer",
        "name": result["name"],
        "role": result["role"]
    }


@router.get("/me")
def auth_me(current_user=Depends(get_current_user)):
    # 토큰 기반 식별 정보
    return success(current_user)
