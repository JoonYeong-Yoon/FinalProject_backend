# JWT 생성/검증 관련 import
from datetime import datetime, timedelta
from jose import jwt, JWTError

# FastAPI 관련 import
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# DB 연결 import
from db.database import get_db

# 모델 import
from models.users_model import get_user_by_email

# 설정 import
from config.settings import settings

# -----------------------------
# OAuth2 패스포트 토큰 설정
# -----------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/web/users/login")
# - 클라이언트가 로그인 후 받을 토큰을 Authorization 헤더에서 자동 추출
# - Swagger UI에서 token 입력란 생성

# -----------------------------
# JWT 액세스 토큰 생성 함수
# -----------------------------
def create_access_token(data: dict):
    """
    JWT 액세스 토큰 생성
    - data: payload에 넣을 정보 dict (예: {"email": "user@example.com"})
    반환: JWT 문자열
    """
    payload = data.copy()
    # 만료시간 설정 (UTC 기준)
    payload["exp"] = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # JWT 인코딩 (HS256)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

# -----------------------------
# 현재 로그인 사용자 조회 함수 (의존성)
# -----------------------------
def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    """
    요청 헤더에서 토큰 추출 후 사용자 확인
    - token: Authorization 헤더에서 Bearer 토큰 자동 주입
    - db: DB 연결
    반환: 사용자 dict (id, email, name)
    """

    # 1. JWT 디코딩 및 유효성 검사
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("email")  # payload에서 이메일 추출
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰에 이메일 없음"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="잘못된 또는 만료된 토큰입니다."
        )

    # 2. DB 조회: 이메일로 사용자 정보 확인 (모델 함수 사용)
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다."
        )

    # 3. 필요한 필드만 반환
    return {"id": user["id"], "email": user["email"], "name": user["name"]}
