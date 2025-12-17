# FastAPI의 APIRouter import
from fastapi import APIRouter

# 하위 라우터 import
from .auth_route import router as auth_router      # 로그인 / 회원가입 관련
from .profile_route import router as profile_router  # 사용자 프로필 관련
from .manage_route import router as manage_router    # 사용자 관리 관련 (삭제, 구독 등)

# -----------------------------
# 메인 사용자 라우터 생성
# -----------------------------
router = APIRouter(
    prefix="/users",  # 모든 엔드포인트 URL 앞에 /users 접두사 추가
    tags=["Users"]    # Swagger UI에서 그룹화
)

# 하위 라우터 포함
router.include_router(auth_router, tags=["Users - Auth"])        # 인증 관련 라우터
router.include_router(profile_router, tags=["Users - Profile"])  # 프로필 관련 라우터
router.include_router(manage_router, tags=["Users - Manage"])    # 관리 관련 라우터
