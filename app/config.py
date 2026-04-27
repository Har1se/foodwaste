from pydantic_settings import BaseSettings
from pydantic import validator
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

    # App
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    @validator("SECRET_KEY")
    def secret_key_length(cls, v):
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    class Config:
        env_file = ".env"


settings = Settings()
