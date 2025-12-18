import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# LLM 설정
# ============================================================
LLM_MODEL_MAIN = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))

# ============================================================
# LLM 분석 전용 설정 (선택사항)
# ============================================================
# 운동 루틴 분석은 상대적으로 짧은 응답이면 충분하므로
# 별도 설정을 원한다면 아래 주석 해제
# ANALYSIS_MAX_TOKENS = int(os.getenv("ANALYSIS_MAX_TOKENS", "1500"))

# 또는 기본 LLM_MAX_TOKENS 사용 (권장)
ANALYSIS_MAX_TOKENS = LLM_MAX_TOKENS

# ============================================================
# API 설정
# ============================================================
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))

# ============================================================
# OpenAI 설정
# ============================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("⚠️ OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

# ============================================================
# CORS 설정 (보안 강화)
# ============================================================
# 개발 환경: ALLOWED_ORIGINS="http://localhost:3000,http://localhost:5173"
# 프로덕션: ALLOWED_ORIGINS="https://yourdomain.com"
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

# ============================================================
# ChromaDB 설정
# ============================================================
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "summaries")

# ============================================================
# 로깅 설정
# ============================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "app.log")

# ============================================================
# 기타 설정
# ============================================================
# 운동 루틴 설정
DEFAULT_DIFFICULTY = "중"
DEFAULT_DURATION = 30  # 분

# RAG 설정
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
RAG_SIMILARITY_THRESHOLD = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.5"))

# 임베딩 배치 사이즈
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "100"))
