# app/main.py
"""
FastAPI 진입점 - 라우터 등록 및 공통 미들웨어 설정
"""

from dotenv import load_dotenv
import os

os.environ["LOKY_MAX_CPU_COUNT"] = "4"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routine_recommendation import router as routine_router
from api.coaching import router as coaching_router
from api.activity import router as activity_router

app = FastAPI(title="AI Home Training API", version="1.0")

# 개발 단계에서는 모든 출처 허용. 운영시에는 특정 도메인만 허용하도록 수정.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# 라우터 등록
app.include_router(routine_router)
app.include_router(coaching_router)
app.include_router(activity_router)


@app.get("/health")
async def health():
    """간단 헬스체크"""
    return {"status": "ok"}

@app.get("/")
def read_root():
    # 이 메시지가 뜨면 서버는 정상 작동하는 것입니다.
    return {"message": "Welcome to the API!", "status": "OK"}