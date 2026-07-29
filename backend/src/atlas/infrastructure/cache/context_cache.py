"""Redis cache for latest market context."""

import json

from redis.asyncio import Redis

from atlas.domain.models.market_context import MarketContext

CONTEXT_CACHE_TTL_SECONDS = 60


def _cache_key(symbol: str) -> str:
    return f"context:{symbol.upper()}:latest"


def _context_to_dict(context: MarketContext) -> dict:
    return {
        "symbol": context.instrument.symbol,
        "primary_session": context.primary_session.value,
        "active_sessions": [s.value for s in context.active_sessions],
        "volatility_regime": context.volatility_regime.value,
        "spread_status": context.spread_status.value,
        "structural_bias": context.structural_bias.value,
        "atr_value": str(context.atr_value),
        "atr_percentile": str(context.atr_percentile),
        "computed_at": context.computed_at.isoformat(),
    }


class ContextCache:
    """Cache latest market context per symbol."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def set_latest(self, context: MarketContext) -> None:
        """Store context JSON."""
        key = _cache_key(context.instrument.symbol)
        await self._redis.setex(
            key,
            CONTEXT_CACHE_TTL_SECONDS,
            json.dumps(_context_to_dict(context)),
        )

    async def get_latest(self, symbol: str) -> dict | None:
        """Retrieve cached context dict or None."""
        raw = await self._redis.get(_cache_key(symbol))
        if not raw:
            return None
        return json.loads(raw)
