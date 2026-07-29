"""Strategy engine application service."""

from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from atlas.domain.events.base import DomainEvent
from atlas.domain.models.strategy import StrategyProfile
from atlas.domain.ports.event_bus import EventBusProtocol
from atlas.domain.services.strategy_validation import validate_profile_config
from atlas.infrastructure.cache.strategy_cache import StrategyProfileCache
from atlas.infrastructure.persistence.repositories import (
    StrategyProfileRepository,
    strategy_profile_to_domain,
)

logger = structlog.get_logger(__name__)


class ProfileNotFoundError(Exception):
    """Raised when a strategy profile id does not exist."""

    def __init__(self, profile_id: str) -> None:
        self.profile_id = profile_id
        super().__init__(f"Profile not found: {profile_id}")


class ProfileValidationError(Exception):
    """Raised when profile configuration fails validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass
class StrategyEngineService:
    """Load, validate, and serve strategy profiles."""

    session_factory: async_sessionmaker[AsyncSession]
    event_bus: EventBusProtocol
    profile_cache: StrategyProfileCache

    async def get_active(self) -> StrategyProfile:
        """Return active profile from cache or database."""
        cached = await self.profile_cache.get_active()
        if cached:
            return cached

        async with self.session_factory() as session:
            repo = StrategyProfileRepository(session)
            row = await repo.get_active()
            if not row:
                row = await repo.ensure_default_active()
            profile = strategy_profile_to_domain(row)

        await self.profile_cache.set_active(profile)
        return profile

    async def set_active(self, profile_id: str) -> StrategyProfile:
        """Switch active profile after validation."""
        async with self.session_factory() as session:
            repo = StrategyProfileRepository(session)
            target = await repo.get_by_id(profile_id)
            if not target:
                raise ProfileNotFoundError(profile_id)

            errors = self.validate_profile(target.config)
            if errors:
                raise ProfileValidationError(errors)

            previous = await repo.get_active()
            previous_id = previous.id if previous else None

            activated = await repo.set_active(profile_id)
            if not activated:
                raise ProfileNotFoundError(profile_id)

            profile = strategy_profile_to_domain(activated)

        await self.profile_cache.set_active(profile)
        self.event_bus.publish(
            DomainEvent(
                event_type="strategy.profile.changed",
                correlation_id=profile_id,
                payload={
                    "profile_id": profile.id,
                    "previous_profile_id": previous_id,
                },
            )
        )
        logger.info(
            "strategy_profile_changed",
            profile_id=profile.id,
            previous_profile_id=previous_id,
        )
        return profile

    async def list_profiles(self) -> list[StrategyProfile]:
        """List all strategy profiles."""
        async with self.session_factory() as session:
            repo = StrategyProfileRepository(session)
            rows = await repo.list_all()
            return [strategy_profile_to_domain(row) for row in rows]

    def validate_profile(self, config: dict) -> list[str]:
        """Validate profile configuration."""
        return validate_profile_config(config)
