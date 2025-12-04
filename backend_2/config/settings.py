# pydantic의 BaseSettings를 사용하여 환경 설정 관리
# BaseSettings를 상속하면 환경 변수나 .env 파일로부터 값을 자동으로 읽어올 수 있음
from pydantic import BaseSettings

# Settings 클래스 정의: 애플리케이션 전반에서 사용할 환경 변수 및 설정값 정의
class Settings(BaseSettings):
    # JWT 토큰 생성에 사용할 비밀 키
    # ⭐ 기본값을 비워두어 .env 값을 반드시 읽도록 변경
    SECRET_KEY: str = ""

    # JWT 토큰 생성에 사용할 알고리즘 (HS256: HMAC + SHA-256)
    ALGORITHM: str = "HS256"

    # 액세스 토큰 만료 시간 (분 단위)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # PostgreSQL 데이터베이스 연결 URL
    # 형식: postgresql://<username>:<password>@<host>:<port>/<database_name>
    DATABASE_URL: str = "postgresql://postgres:postgres@192.168.0.38:5432/home_training_db"

    # Pydantic 설정 클래스 Config 정의
    # .env 파일로부터 설정값을 읽어오도록 지정
    class Config:
        env_file = ".env"          # ⭐ 무조건 .env 읽도록 명시
        env_file_encoding = "utf-8"

# Settings 클래스 인스턴스 생성
# 이 객체를 통해 프로젝트 전반에서 환경 변수와 설정값 접근 가능
settings = Settings()
