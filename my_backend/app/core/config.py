# app/core/config.py
"""
환경 설정 로더
- .env를 통해 값을 읽어오며, 기본값을 제공
"""
import os
from dotenv import load_dotenv

load_dotenv()

POSTGRES_DB = os.getenv("POSTGRES_DB", "home_training_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")   # Docker 환경에서는 'db' 호스트 사용
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))

AI_MODELS_DIR = os.getenv("AI_MODELS_DIR", "/app/ai_models")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")