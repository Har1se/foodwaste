from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://rescuebite:rescuebite@db:5432/rescuebite_db"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Security
    SECRET_KEY: str = "CHANGE_ME_minimum_32_characters_long_random_string_here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Kaspi Pay (optional for now)
    KASPI_API_KEY: str = "CHANGE_ME"
    KASPI_MERCHANT_ID: str = "CHANGE_ME"
    KASPI_WEBHOOK_SECRET: str = "CHANGE_ME"

    # S3 Storage
    S3_BUCKET: str = "rescuebite-media"
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "CHANGE_ME"
    S3_SECRET_KEY: str = "CHANGE_ME"

    # Email (SMTP)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@rescuebite.kz"
    FRONTEND_URL: str = "http://localhost:3000"

    # App
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    ENABLE_RATE_LIMIT: bool = False
    DEV_AUTO_VERIFY_EMAIL: bool = True
    DEV_AUTO_APPROVE_VENDORS: bool = True
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    model_config = {"env_file": ".env"}


settings = Settings()
