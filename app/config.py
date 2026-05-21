from typing import List, Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

_PLACEHOLDER_PREFIXES = ("CHANGE_ME", "your_", "replace_")


def _is_placeholder(v: str) -> bool:
    return any(v.startswith(p) for p in _PLACEHOLDER_PREFIXES)


class Settings(BaseSettings):
    # ── Database ────────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://rescuebite:rescuebite@postgres:5432/rescuebite_db"

    # ── Redis ────────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"

    # ── Security ─────────────────────────────────────────────────────────────────
    # Accepts both SECRET_KEY (legacy) and JWT_SECRET_KEY (platform standard).
    # JWT_SECRET_KEY takes precedence if both are set.
    SECRET_KEY: str = "rescuebite_dev_key_minimum_32chars_long"
    JWT_SECRET_KEY: Optional[str] = None          # Alias for SECRET_KEY
    JWT_REFRESH_SECRET_KEY: str = ""              # Optional separate refresh token secret
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200      # 30 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Email — SMTP (Gmail / Yandex / SendGrid relay) ───────────────────────────
    # For SendGrid: SMTP_HOST=smtp.sendgrid.net, SMTP_USER=apikey, SMTP_PASSWORD=<API_KEY>
    # Or set EMAIL_API_KEY and EMAIL_FROM_ADDRESS for simplified config.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@rescuebite.kz"
    EMAIL_API_KEY: str = ""       # SendGrid/Mailgun API key (mapped to SMTP_PASSWORD)
    EMAIL_FROM_ADDRESS: str = ""  # Alias for SMTP_FROM
    FRONTEND_URL: str = "http://localhost:3000"

    # ── CORS ─────────────────────────────────────────────────────────────────────
    # CORS_ORIGINS: comma-separated string (platform standard).
    # ALLOWED_ORIGINS: JSON list (legacy). CORS_ORIGINS takes precedence if set.
    CORS_ORIGINS: str = ""
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://rescuebite.deployrocks.com",
        "https://rescuebite-api.deployrocks.com",
        "https://foodwaste-1-fe33.onrender.com",
        "https://foodwaste-gcjn.onrender.com",
    ]

    # ── Ports (for documentation / docker-compose variable expansion) ────────────
    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 3000

    # ── Kaspi Pay ─────────────────────────────────────────────────────────────────
    KASPI_API_KEY: str = "dev_placeholder"
    KASPI_MERCHANT_ID: str = "dev_placeholder"
    KASPI_WEBHOOK_SECRET: str = "dev_placeholder"

    # ── S3 Storage ────────────────────────────────────────────────────────────────
    S3_BUCKET: str = "rescuebite-media"
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "dev_placeholder"
    S3_SECRET_KEY: str = "dev_placeholder"

    # ── App ───────────────────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    ENABLE_RATE_LIMIT: bool = True
    DEV_AUTO_VERIFY_EMAIL: bool = True
    DEV_AUTO_APPROVE_VENDORS: bool = True

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_set(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        if _is_placeholder(v):
            raise ValueError(
                "SECRET_KEY is still the default placeholder — "
                "set a real random value in .env or environment variables"
            )
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def database_url_must_be_set(cls, v: str) -> str:
        if not v or "CHANGE_ME" in v:
            raise ValueError("DATABASE_URL must be configured")
        return v

    @field_validator("REDIS_URL")
    @classmethod
    def redis_url_must_be_set(cls, v: str) -> str:
        if not v or "CHANGE_ME" in v:
            raise ValueError("REDIS_URL must be configured")
        return v

    @model_validator(mode="after")
    def apply_aliases(self) -> "Settings":
        # JWT_SECRET_KEY overrides SECRET_KEY if provided
        if self.JWT_SECRET_KEY and len(self.JWT_SECRET_KEY) >= 32:
            self.SECRET_KEY = self.JWT_SECRET_KEY

        # EMAIL_FROM_ADDRESS overrides SMTP_FROM
        if self.EMAIL_FROM_ADDRESS:
            self.SMTP_FROM = self.EMAIL_FROM_ADDRESS

        # EMAIL_API_KEY → use as SMTP_PASSWORD with SendGrid relay
        if self.EMAIL_API_KEY and not self.SMTP_PASSWORD:
            self.SMTP_PASSWORD = self.EMAIL_API_KEY
            if not self.SMTP_HOST:
                self.SMTP_HOST = "smtp.sendgrid.net"
            if not self.SMTP_USER:
                self.SMTP_USER = "apikey"

        # CORS_ORIGINS (comma-separated) overrides ALLOWED_ORIGINS
        if self.CORS_ORIGINS:
            self.ALLOWED_ORIGINS = [s.strip() for s in self.CORS_ORIGINS.split(",") if s.strip()]

        return self

    model_config = {"env_file": ".env"}


settings = Settings()
