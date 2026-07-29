"""Strategy engine port."""

from typing import Protocol

from atlas.domain.models.strategy import StrategyProfile


class StrategyEngineServiceProtocol(Protocol):
    """Manage strategy profiles and active configuration."""

    async def get_active(self) -> StrategyProfile:
        """Return the currently active strategy profile."""
        ...

    async def set_active(self, profile_id: str) -> StrategyProfile:
        """Switch active profile; raises ValueError on invalid profile."""
        ...

    async def list_profiles(self) -> list[StrategyProfile]:
        """List all strategy profiles."""
        ...

    def validate_profile(self, config: dict) -> list[str]:
        """Validate profile config; return error messages (empty if valid)."""
        ...
