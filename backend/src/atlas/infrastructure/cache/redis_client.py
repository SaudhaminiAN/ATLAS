"""Redis client wrapper."""

from redis.asyncio import Redis


async def create_redis(url: str) -> Redis:
    """Create async Redis client."""
    return Redis.from_url(url, decode_responses=True)


async def check_redis(redis: Redis) -> bool:
    """Return True if Redis responds to PING."""
    try:
        return bool(await redis.ping())
    except Exception:
        return False
