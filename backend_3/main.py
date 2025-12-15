# ===============================
# FastAPI import
# ===============================
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# ===============================
# 🔥 라우터 import (리팩토링 기준)
# ===============================
from routes.users.auth import router as auth_router
from routes.users.profile import router as users_router
from routes.users.subscriptions import router as subscriptions_router
from routes.users.videos import router as videos_router

from routes.users.admin.users import router as admin_users_router
from routes.users.admin.logs import router as admin_logs_router

from ios.health import router as ios_router
from config.settings import settings

# ===============================
# 🔥 FastAPI 앱 생성
# ===============================
app = FastAPI(
    title="AI Trainer Backend",
    description="FastAPI backend for AI 홈트레이닝 서비스",
    version="1.0.0"
)

# ===============================
# 🔥 CORS 설정
# ===============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# 🔥 라우터 등록
# ===============================

# ⭐ iOS HealthKit
app.include_router(ios_router, prefix="/ios", tags=["ios"])

# 🔐 인증 (회원가입 / 로그인 / auth me)
app.include_router(auth_router, prefix="/web/auth")

# 👤 내 정보 (프로필 조회/수정/탈퇴)
app.include_router(users_router, prefix="/web/users")

# 💳 구독
app.include_router(subscriptions_router, prefix="/web/subscriptions")

# 🎥 비디오
app.include_router(videos_router, prefix="/web/videos")

# 🛠 관리자 - 유저 관리
app.include_router(admin_users_router, prefix="/admin")

# 📜 관리자 - 로그
app.include_router(admin_logs_router, prefix="/admin")

# ===============================
# 🔥 글로벌 예외 핸들러
# ===============================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "message": "Internal server error"
            }
        }
    )

# ===============================
# 🔥 테스트용 루트
# ===============================
@app.get("/")
def root():
    return {
        "status": "server running",
        "service": "AI Trainer Backend",
        "web_endpoints": "/web/*",
        "admin_endpoints": "/admin/*",
        "ios_endpoints": "/ios/*"
    }

# ===============================
# 🔥 uvicorn 실행
# ===============================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
