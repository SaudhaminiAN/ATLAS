"""User persistence."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from atlas.domain.models.user import User
from atlas.infrastructure.persistence.models import UserModel


def user_to_domain(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class UserRepository:
    """User account persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.email == email.lower())
        )
        row = result.scalar_one_or_none()
        return user_to_domain(row) if row else None

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.id == user_id))
        row = result.scalar_one_or_none()
        return user_to_domain(row) if row else None

    async def get_password_hash(self, email: str) -> str | None:
        result = await self._session.execute(
            select(UserModel.password_hash).where(UserModel.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def create(self, email: str, password_hash: str) -> User:
        now = datetime.now(UTC)
        model = UserModel(
            id=uuid4(),
            email=email.lower(),
            password_hash=password_hash,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return user_to_domain(model)

    async def email_exists(self, email: str) -> bool:
        result = await self._session.execute(
            select(UserModel.id).where(UserModel.email == email.lower())
        )
        return result.scalar_one_or_none() is not None
