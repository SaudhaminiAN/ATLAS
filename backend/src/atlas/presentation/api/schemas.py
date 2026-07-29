"""API response envelopes."""

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseMeta(BaseModel):
    """Standard response metadata."""

    request_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ApiError(BaseModel):
    """Standard error shape."""

    code: str
    message: str
    details: list[Any] = Field(default_factory=list)


class ApiEnvelope(BaseModel, Generic[T]):
    """Consistent API response wrapper."""

    success: bool
    data: T | None = None
    error: ApiError | None = None
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
