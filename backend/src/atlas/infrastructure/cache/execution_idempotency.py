"""Execution idempotency cache."""

from redis.asyncio import Redis


class ExecutionIdempotencyCache:
    """Prevent duplicate order submission for the same decision."""

    def __init__(self, redis: Redis, ttl_seconds: int = 300) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    def _key(self, idempotency_key: str) -> str:
        return f"execution:idem:{idempotency_key}"

    async def try_acquire(self, idempotency_key: str) -> bool:
        result = await self._redis.set(
            self._key(idempotency_key),
            "1",
            nx=True,
            ex=self._ttl_seconds,
        )
        return result is not None
