# ============================================
# 🛠 JWT 생성 & 인증 관련 설정
# ============================================

from datetime import datetime, timedelta
from jose import jwt, JWTError

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from db.database import get_db
from models.users_model import get_user_by_id
from config.settings import settings


# ---------------------------------------------------
# OAuth2 설정 (로그인 URL)
# ---------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/web/users/login")


# ---------------------------------------------------
# JWT 액세스 토큰 생성
# ---------------------------------------------------
def create_access_token(data: dict):
    """
    JWT 토큰 생성
    - data: payload로 들어갈 값 (예: {"sub": user_id, "role": True})
    """
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ---------------------------------------------------
# 현재 로그인 사용자 조회
# ---------------------------------------------------
def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    """
    Authorization 헤더에서 JWT 추출 → 디코딩 → 사용자 검증
    """
    try:
        # JWT 디코딩
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰에 user_id가 없습니다."
            )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="잘못되었거나 만료된 토큰입니다."
        )

    # DB에서 유저 조회
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유저를 찾을 수 없습니다."
        )

    # 👉 최종 반환 (boolean role 적용)
    created_at = user["created_at"].strftime("%Y-%m-%d %H:%M")
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": payload.get("role", False),   # ⭐ 기본값 False = 일반 사용자
        "created_at":created_at
    }


# ---------------------------------------------------
# 관리자 전용 권한 체크 함수
# ---------------------------------------------------
def admin_required(current_user = Depends(get_current_user)):
    """
    관리자만 접근 허용하는 의존성 함수
    - role=True → 관리자
    - role=False → 일반 사용자
    """
    if not current_user["role"]:   # ⭐ False면 관리자 아님
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자만 접근할 수 있습니다."
        )
    
    return current_user
