from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from db.database import get_db
from models.users import get_user_by_id
from core.users.exceptions import AppException
from services.users.jwt import decode_token

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/web/auth/login"
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db)
):
    try:
        payload = decode_token(token)

        user_id: str = payload.get("sub")
        role: str = payload.get("role")

        if not user_id or not role:
            raise AppException(
                status_code=401,
                message="Invalid token payload",
                code="INVALID_TOKEN"
            )

    except JWTError:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="잘못되었거나 만료된 토큰입니다.",
            code="TOKEN_EXPIRED"
        )

    user = get_user_by_id(db, user_id)
    if not user:
        raise AppException(
            status_code=401,
            message="유저를 찾을 수 없습니다.",
            code="USER_NOT_FOUND"
        )
    
    role_bool = user.get("role", False)
    role = "admin" if role_bool is True else "user"
    
    return {
        "id": str(user["id"]),
        "email": user["email"],
        "name": user["name"],
        "role": role
    }
