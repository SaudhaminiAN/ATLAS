"""Redis cache for active strategy profile."""

import json
from datetime import datetime
from decimal import Decimal

from redis.asyncio import Redis

from atlas.domain.models.enums import Direction, Timeframe, TradingSession
from atlas.domain.models.strategy import StrategyProfile

STRATEGY_CACHE_KEY = "strategy:active"
STRATEGY_CACHE_TTL_SECONDS = 300


def _profile_to_dict(profile: StrategyProfile) -> dict:
    return {
        "id": profile.id,
        "name": profile.name,
        "min_confluence_score": str(profile.min_confluence_score),
        "enabled_directions": [d.value for d in profile.enabled_directions],
        "confluence_weights": {k: str(v) for k, v in profile.confluence_weights.items()},
        "active_timeframes": [tf.value for tf in profile.active_timeframes],
        "allowed_sessions": [s.value for s in profile.allowed_sessions],
        "validation_rule_flags": profile.validation_rule_flags,
        "is_active": profile.is_active,
        "updated_at": profile.updated_at.isoformat(),
    }


def _profile_from_dict(data: dict) -> StrategyProfile:
    return StrategyProfile(
        id=data["id"],
        name=data["name"],
        min_confluence_score=Decimal(data["min_confluence_score"]),
        enabled_directions=tuple(Direction(d) for d in data["enabled_directions"]),
        confluence_weights={k: Decimal(v) for k, v in data["confluence_weights"].items()},
        active_timeframes=tuple(Timeframe(tf) for tf in data["active_timeframes"]),
        allowed_sessions=tuple(TradingSession(s) for s in data["allowed_sessions"]),
        validation_rule_flags=dict(data["validation_rule_flags"]),
        is_active=bool(data["is_active"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
    )


class StrategyProfileCache:
    """Cache active strategy profile."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get_active(self) -> StrategyProfile | None:
        """Retrieve cached active profile or None."""
        raw = await self._redis.get(STRATEGY_CACHE_KEY)
        if not raw:
            return None
        return _profile_from_dict(json.loads(raw))

    async def set_active(self, profile: StrategyProfile) -> None:
        """Store active profile with TTL."""
        await self._redis.setex(
            STRATEGY_CACHE_KEY,
            STRATEGY_CACHE_TTL_SECONDS,
            json.dumps(_profile_to_dict(profile)),
        )

    async def invalidate(self) -> None:
        """Clear cached active profile."""
        await self._redis.delete(STRATEGY_CACHE_KEY)
