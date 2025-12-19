from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.file_upload_api import router as file_upload_router
from app.api.auto_upload_api import router as auto_upload_router
from app.api.similar_api import router as similar_router
from app.api.chat_api import router as chat_router
from app.api.user_api import router as user_router

from fastapi import APIRouter
from app.core.vector_store import collection, search_similar_summaries

from dotenv import load_dotenv

load_dotenv()

print("🔥🔥 FASTAPI SERVER LOADED: VERSION TEST 🔥🔥")

# ==========================
# 1) FastAPI 앱 생성
# ==========================
app = FastAPI(
    title="Health Trainer API",
    description="DB → JSON → AI 분석 트레이너 서비스",
    version="0.1.0",
    default_response_class=ORJSONResponse,
)

# ==========================
# 2) CORS 설정
# ==========================
app.add_middleware(
    CORSMiddleware,
    # allow_origins=["*"],
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# 3) 기존 라우터 등록
# ==========================
app.include_router(file_upload_router)
app.include_router(auto_upload_router)
app.include_router(similar_router)
app.include_router(chat_router)
app.include_router(user_router)

vectordb_router = APIRouter(prefix="/api/vectordb", tags=["VectorDB"])


@vectordb_router.get("/status")
async def get_vectordb_status():
    """VectorDB 전체 상태 확인"""
    try:
        count = collection.count()
        all_data = collection.get(include=["metadatas"])

        user_data = {}
        for metadata in all_data.get("metadatas", []):
            user_id = metadata.get("user_id", "unknown")
            date = metadata.get("date", "unknown")

            user_data.setdefault(user_id, []).append(date)

        user_summary = {
            user_id: {
                "count": len(dates),
                "dates": sorted(dates, reverse=True),
            }
            for user_id, dates in user_data.items()
        }

        return {
            "status": "ok",
            "total_count": count,
            "users": user_summary,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }


@vectordb_router.get("/user/{user_id}")
async def get_user_vectordb_data(user_id: str):
    """특정 사용자 VectorDB 데이터 조회"""
    try:
        result = search_similar_summaries(
            query_dict={"query": "health summary"},
            user_id=user_id,
            top_k=100,
        )

        similar_days = result.get("similar_days", [])
        sorted_days = sorted(
            similar_days,
            key=lambda x: x.get("date", ""),
            reverse=True,
        )

        return {
            "status": "ok",
            "user_id": user_id,
            "count": len(sorted_days),
            "data": [
                {
                    "date": day.get("date"),
                    "summary_preview": day.get("summary_text", "")[:100],
                    "data_keys": list(day.get("raw", {}).keys()),
                }
                for day in sorted_days
            ],
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }


app.include_router(vectordb_router)


# ==========================
# 4) 기본 라우트
# ==========================
@app.get("/")
def root():
    return {"message": "API is running (VectorDB mode)"}


# ==========================
# 5) Global Exception Handlers
# ==========================
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"success": False, "error": exc.errors()},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": str(exc),
            "type": type(exc).__name__,
        },
    )
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
