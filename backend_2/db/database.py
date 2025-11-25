# SQLAlchemy의 create_engine 함수 import
# DB 연결 엔진 생성에 사용
from sqlalchemy import create_engine

# 설정값 import
# settings: config/settings.py에서 정의한 환경 변수 객체
from config.settings import settings

# SQLAlchemy Engine 생성
# settings.DATABASE_URL: PostgreSQL 연결 URL
# future=True: SQLAlchemy 2.x 스타일 사용 (향후 버전 호환)
engine = create_engine(settings.DATABASE_URL, future=True)

# DB 연결 세션/커넥션 제공용 함수
# FastAPI에서 Dependency로 사용 가능
def get_db():
    # engine.connect()를 context manager로 사용
    # 연결이 끝나면 자동으로 close 처리
    with engine.connect() as conn:
        # yield를 사용하여 generator 형태로 반환
        # FastAPI에서 dependency injection 시 사용됨
        yield conn
