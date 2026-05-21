import base64
import json
from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    total: Optional[int] = None
    limit: int
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None


class CursorPage(BaseModel, Generic[T]):
    data: List[T]
    pagination: PaginationMeta


def encode_cursor(data: dict) -> str:
    return base64.b64encode(json.dumps(data).encode()).decode()


def decode_cursor(cursor: str) -> Optional[dict]:
    try:
        return json.loads(base64.b64decode(cursor.encode()).decode())
    except Exception:
        return None
