"""Redis cache for latest OHLCV bars."""

import json

from redis.asyncio import Redis

from atlas.domain.models.enums import Timeframe
from atlas.domain.models.ohlcv import OHLCVBar

BAR_CACHE_TTL_SECONDS = 60


def _cache_key(symbol: str, timeframe: Timeframe) -> str:
    return f"bars:{symbol.upper()}:{timeframe.value}:latest"


class BarCache:
    """Cache latest bar per symbol/timeframe."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def set_latest(self, bar: OHLCVBar) -> None:
        """Store latest bar JSON."""
        payload = {
            "symbol": bar.instrument.symbol,
            "timeframe": bar.timeframe.value,
            "open_time": bar.open_time.isoformat(),
            "open": str(bar.open),
            "high": str(bar.high),
            "low": str(bar.low),
            "close": str(bar.close),
            "volume": str(bar.volume),
            "is_outlier": bar.is_outlier,
            "quality_flags": bar.quality_flags,
        }
        key = _cache_key(bar.instrument.symbol, bar.timeframe)
        await self._redis.setex(key, BAR_CACHE_TTL_SECONDS, json.dumps(payload))

    async def get_latest(self, symbol: str, timeframe: Timeframe) -> dict | None:
        """Retrieve cached bar dict or None."""
        raw = await self._redis.get(_cache_key(symbol, timeframe))
        if not raw:
            return None
        return json.loads(raw)
