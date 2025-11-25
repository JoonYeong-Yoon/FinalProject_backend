# FastAPI import
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 라우터 import
from routes import subscription_route, video_route
from routes.users import router as users_router

# -----------------------------
# FastAPI 앱 생성
# -----------------------------
app = FastAPI(
    title="AI Trainer Backend",  # Swagger UI 타이틀
    description="FastAPI backend for AI 홈트레이닝 서비스",  # Swagger 설명
    version="1.0.0"  # API 버전
)

# -----------------------------
# CORS 설정
# -----------------------------
origins = [
    "http://localhost:3000",  # React 개발 서버
    "http://127.0.0.1:3000",
    "http://192.168.0.12:3000",  # 내부 네트워크 접속 가능
    "http://localhost:5173",  # Vite 개발 서버
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 허용 도메인
    allow_credentials=True,  # 쿠키/인증 허용
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

# -----------------------------
# 라우터 등록
# -----------------------------
app.include_router(users_router, prefix="/web")  # 사용자 관련 API
app.include_router(subscription_route.router, prefix="/web/subscription")  # 구독 관련 API
app.include_router(video_route.router, prefix="/web/video")  # 비디오 업로드 API

# -----------------------------
# 루트 엔드포인트
# -----------------------------
@app.get("/")
def root():
    """
    서버 상태 확인용 엔드포인트
    반환: 서버 상태, 서비스 이름, 웹 엔드포인트 안내
    """
    return {
        "status": "server running",
        "service": "AI Trainer Backend",
        "web_endpoints": "/web/*"
    }

# -----------------------------
# uvicorn 실행 (직접 실행 시)
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    # host="0.0.0.0" -> 외부 접속 가능
    # reload=True -> 코드 변경 시 자동 재시작
    # 콘솔에 python main.py 입력해서 백엔드 가동