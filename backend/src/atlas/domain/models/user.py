"""User domain model."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class User:
    """Registered application user."""

    id: UUID
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class TokenPair:
    """JWT access and refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
