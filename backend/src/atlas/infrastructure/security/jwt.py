"""JWT token creation and validation."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt

_ACCESS_TYPE = "access"
_REFRESH_TYPE = "refresh"


class TokenError(Exception):
    """Invalid or expired token."""


def create_access_token(
    *,
    user_id: UUID,
    secret: str,
    expire_minutes: int,
) -> tuple[str, int]:
    expires_in = expire_minutes * 60
    payload = {
        "sub": str(user_id),
        "type": _ACCESS_TYPE,
        "exp": datetime.now(UTC) + timedelta(minutes=expire_minutes),
        "iat": datetime.now(UTC),
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token, expires_in


def create_refresh_token(
    *,
    user_id: UUID,
    secret: str,
    expire_days: int,
) -> str:
    payload = {
        "sub": str(user_id),
        "type": _REFRESH_TYPE,
        "exp": datetime.now(UTC) + timedelta(days=expire_days),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str, secret: str, *, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise TokenError("Invalid token") from exc
    if payload.get("type") != expected_type:
        raise TokenError("Invalid token type")
    return payload


def user_id_from_payload(payload: dict[str, Any]) -> UUID:
    sub = payload.get("sub")
    if not sub:
        raise TokenError("Missing subject")
    return UUID(str(sub))
