from pydantic_settings import BaseSettings


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

    # PostgreSQL (Docker uchun)
    POSTGRES_DB: str = ""
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"  # .env dagi ortiqcha fieldlarni e'tiborsiz qoldiradi


settings = Settings()