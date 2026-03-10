from typing import List
from zoneinfo import ZoneInfo

from pydantic import field_validator
from pydantic_settings import BaseSettings

TZ = ZoneInfo("Asia/Tashkent")


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_SECRET: str = ""
    BASE_URL: str = "http://localhost:8000"
    MEDIA_DIR: str = "media"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173"]

    # PostgreSQL (Docker uchun)
    POSTGRES_DB: str = ""
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()