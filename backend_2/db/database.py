# db/database.py

from config.settings import settings
from sqlalchemy import create_engine

# ---------------------------------
# PostgreSQL DB URL 확인용 (선택)
# ---------------------------------
print("🚀 DATABASE_URL =", settings.DATABASE_URL)

# ---------------------------------
# SQLAlchemy Engine 생성
# ---------------------------------
# future=True → SQLAlchemy 2.x 스타일
engine = create_engine(
    settings.DATABASE_URL,
    echo=True,        # SQL 출력 (디버깅 쉽게)
    future=True
)

# ---------------------------------
# FastAPI 의존성 주입(DB 연결 제공)
# ---------------------------------
def get_db():
    """
    FastAPI 라우터에서 DB 연결을 주입할 때 사용.
    RAW SQL 방식이므로 Connection 객체를 반환한다.
    """
    with engine.connect() as conn:
        yield conn
