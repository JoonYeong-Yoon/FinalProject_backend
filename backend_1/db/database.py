from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# -------------------------------
# 🚀 PostgreSQL 연결 정보 설정
# -------------------------------
SQLALCHEMY_DATABASE_URL = (
    "postgresql://test:test@192.168.0.38:3308/postgres"
)

# PostgreSQL 엔진 생성
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 세션 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 베이스 모델 생성
Base = declarative_base()

# DB 세션 제공 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
