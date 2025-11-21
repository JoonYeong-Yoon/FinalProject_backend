from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ========================
# 🔥 라우터 import
# ========================

# Web 전용 라우터들
from web.routes.users import router as users_router
from web.routes.video import router as video_router
from web.routes.subscription import router as subscription_router

# iOS 전용 라우터
from ios.health import router as health_router


# ========================
# 🔥 FastAPI 기본 정보
# ========================
app = FastAPI(
    title="AI Trainer Backend",
    description="FastAPI backend for AI 홈트레이닝 서비스",
    version="1.0.0"
)


# ========================
# 🔥 CORS 설정
# ========================
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://192.168.0.12:3000",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========================
# 🔥 라우터 등록
# ========================
# 웹 서비스 API
app.include_router(users_router, prefix="/web/users", tags=["Users"])
app.include_router(video_router, prefix="/web/video", tags=["Video"])
app.include_router(subscription_router, prefix="/web/subscription", tags=["Subscription"])

# iOS HealthKit API
app.include_router(health_router, prefix="/ios/health", tags=["HealthData"])


# ========================
# 🔥 기본 Root API
# ========================
@app.get("/")
def root():
    return {
        "status": "server running",
        "service": "AI Trainer Backend",
        "web_endpoints": "/web/*",
        "ios_endpoints": "/ios/*"
    }
