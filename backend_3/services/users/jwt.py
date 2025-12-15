from datetime import datetime, timedelta
from jose import jwt

from config.settings import settings
from core.users.security import ROLE_SCOPES


def create_access_token(payload: dict) -> str:
    """
    payload 예시:
    {
        "sub": user_id,
        "role": "admin" | "user"
    }
    """
    to_encode = payload.copy()

    role = payload.get("role", "user")
    scopes = ROLE_SCOPES.get(role, [])

    expire = datetime.utcnow() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({
        "scopes": scopes,
        "exp": expire
    })

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM]
    )
