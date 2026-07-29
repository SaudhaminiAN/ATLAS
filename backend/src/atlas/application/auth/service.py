"""Authentication application service."""

from dataclasses import dataclass
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from atlas.domain.models.user import TokenPair, User
from atlas.infrastructure.persistence.user_repository import UserRepository
from atlas.infrastructure.security.jwt import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    user_id_from_payload,
)
from atlas.infrastructure.security.password import hash_password, verify_password

logger = structlog.get_logger(__name__)


class AuthError(Exception):
    """Authentication or registration failure."""


@dataclass
class AuthService:
    """Register, login, and refresh JWT tokens."""

    session_factory: async_sessionmaker[AsyncSession]
    jwt_secret: str
    access_expire_minutes: int
    refresh_expire_days: int
    registration_enabled: bool = True

    async def register(self, email: str, password: str) -> User:
        if not self.registration_enabled:
            raise AuthError("Registration is disabled")
        normalized = email.strip().lower()
        if not normalized or "@" not in normalized:
            raise AuthError("Invalid email address")
        if len(password) < 8:
            raise AuthError("Password must be at least 8 characters")

        async with self.session_factory() as session:
            repo = UserRepository(session)
            if await repo.email_exists(normalized):
                raise AuthError("Email already registered")
            user = await repo.create(normalized, hash_password(password))
            logger.info("user_registered", user_id=str(user.id), email=user.email)
            return user

    async def login(self, email: str, password: str) -> tuple[User, TokenPair]:
        normalized = email.strip().lower()
        async with self.session_factory() as session:
            repo = UserRepository(session)
            user = await repo.get_by_email(normalized)
            if user is None or not user.is_active:
                raise AuthError("Invalid email or password")
            stored_hash = await repo.get_password_hash(normalized)
            if stored_hash is None or not verify_password(password, stored_hash):
                raise AuthError("Invalid email or password")

        tokens = self._issue_tokens(user.id)
        logger.info("user_logged_in", user_id=str(user.id))
        return user, tokens

    async def refresh(self, refresh_token: str) -> TokenPair:
        try:
            payload = decode_token(refresh_token, self.jwt_secret, expected_type="refresh")
            user_id = user_id_from_payload(payload)
        except (TokenError, ValueError) as exc:
            raise AuthError("Invalid refresh token") from exc

        async with self.session_factory() as session:
            user = await UserRepository(session).get_by_id(user_id)
            if user is None or not user.is_active:
                raise AuthError("Invalid refresh token")

        return self._issue_tokens(user_id)

    async def get_user(self, user_id: UUID) -> User | None:
        async with self.session_factory() as session:
            return await UserRepository(session).get_by_id(user_id)

    def verify_access_token(self, token: str) -> UUID:
        try:
            payload = decode_token(token, self.jwt_secret, expected_type="access")
            return user_id_from_payload(payload)
        except (TokenError, ValueError) as exc:
            raise AuthError("Invalid or expired token") from exc

    def _issue_tokens(self, user_id: UUID) -> TokenPair:
        access, expires_in = create_access_token(
            user_id=user_id,
            secret=self.jwt_secret,
            expire_minutes=self.access_expire_minutes,
        )
        refresh = create_refresh_token(
            user_id=user_id,
            secret=self.jwt_secret,
            expire_days=self.refresh_expire_days,
        )
        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            token_type="bearer",
            expires_in=expires_in,
        )
