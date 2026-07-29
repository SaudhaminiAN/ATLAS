"""Redis-backed API rate limiting."""

from redis.asyncio import Redis


class ApiRateLimiter:
    """Fixed-window counter per client key."""

    def __init__(self, redis: Redis, window_seconds: int = 60) -> None:
        self._redis = redis
        self._window = window_seconds

    def _key(self, client_key: str) -> str:
        return f"ratelimit:{client_key}"

    async def allow(self, client_key: str, limit: int) -> bool:
        if limit <= 0:
            return True

        key = self._key(client_key)
        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, self._window)
        return count <= limit

    async def retry_after(self, client_key: str) -> int:
        ttl = await self._redis.ttl(self._key(client_key))
        return max(ttl, 1)
