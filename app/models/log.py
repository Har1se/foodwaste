from datetime import datetime, timezone
from typing import Optional

from sqlmodel import SQLModel, Field
import sqlalchemy as sa


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SystemLog(SQLModel, table=True):
    __tablename__ = "system_logs"
    __table_args__ = (
        sa.Index("ix_syslog_user_time", "user_id", "created_at"),
        sa.Index("ix_syslog_endpoint", "endpoint"),
        sa.Index("ix_syslog_status", "response_status"),
        sa.Index("ix_syslog_created_at", "created_at"),
        sa.Index("ix_syslog_level", "level"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, index=True)
    role: Optional[str] = Field(default=None, max_length=20)
    endpoint: str = Field(max_length=255)
    method: str = Field(max_length=10)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    request_body: Optional[str] = Field(default=None, max_length=2000)
    response_status: int
    error_message: Optional[str] = Field(default=None, max_length=1000)
    error_traceback: Optional[str] = Field(default=None, max_length=5000)
    duration_ms: int = Field(default=0)
    level: str = Field(default="info", max_length=10)  # info | warning | error
    created_at: datetime = Field(default_factory=_utcnow)
