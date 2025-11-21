from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from db.database import get_db
from models.models import User

SECRET_KEY = "secret123"   # 나중에 .env로 옮기기
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# 로그인할 때 tokenUrl은 /users/login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


# 🔥 토큰 생성 함수 (하늘이 쓰던 것 그대로 남겨둠)
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# 🔥 토큰에서 user_id 빼내서 User 객체를 반환하는 함수
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        # 토큰 decode
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰에 user_id 없음.",
            )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다.",
        )

    # DB에서 해당 유저 찾기
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다."
        )

    return user
