"""Auth service unit tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from atlas.application.auth.service import AuthError, AuthService
from atlas.domain.models.user import User
from datetime import UTC, datetime
from uuid import uuid4


def _user() -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid4(),
        email="trader@example.com",
        is_active=True,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def service() -> AuthService:
    session_factory = MagicMock()
    return AuthService(
        session_factory=session_factory,
        jwt_secret="test-secret-key-for-pytest-only-32chars",
        access_expire_minutes=30,
        refresh_expire_days=7,
    )


def test_issue_and_verify_access_token(service: AuthService) -> None:
    user = _user()
    tokens = service._issue_tokens(user.id)
    verified_id = service.verify_access_token(tokens.access_token)
    assert verified_id == user.id


def test_verify_rejects_refresh_token_as_access(service: AuthService) -> None:
    user = _user()
    tokens = service._issue_tokens(user.id)
    with pytest.raises(AuthError):
        service.verify_access_token(tokens.refresh_token)


@pytest.mark.asyncio
async def test_register_rejects_short_password(service: AuthService) -> None:
    with pytest.raises(AuthError, match="8 characters"):
        await service.register("user@example.com", "short")
