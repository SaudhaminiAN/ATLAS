"""Pipeline deduplication cache."""

from datetime import datetime

from redis.asyncio import Redis

from atlas.domain.models.enums import Timeframe


def _dedupe_key(symbol: str, timeframe: Timeframe, open_time: datetime) -> str:
    return f"pipeline:dedupe:{symbol.upper()}:{timeframe.value}:{open_time.isoformat()}"


class PipelineDedupeCache:
    """Prevent duplicate pipeline runs for the same bar."""

    def __init__(self, redis: Redis, ttl_seconds: int = 60) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    async def try_acquire(
        self,
        symbol: str,
        timeframe: Timeframe,
        open_time: datetime,
    ) -> bool:
        """Return True if this run should proceed (key was set)."""
        key = _dedupe_key(symbol, timeframe, open_time)
        result = await self._redis.set(key, "1", nx=True, ex=self._ttl_seconds)
        return result is not None
