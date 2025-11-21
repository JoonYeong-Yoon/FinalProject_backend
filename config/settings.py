from pydantic import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str = "your_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"

settings = Settings()
