"""Rate limiting for AI explanation requests."""

from redis.asyncio import Redis


class ExplanationRateLimiter:
    """Token-bucket style limiter using Redis."""

    def __init__(self, redis: Redis, limit_per_minute: int = 10) -> None:
        self._redis = redis
        self._limit = limit_per_minute

    def _key(self) -> str:
        return "ai:explain:rate"

    async def allow(self) -> bool:
        count = await self._redis.incr(self._key())
        if count == 1:
            await self._redis.expire(self._key(), 60)
        return count <= self._limit
