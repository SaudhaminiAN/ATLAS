"""Redis cache for latest trading decision per symbol."""

import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from redis.asyncio import Redis

from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.enums import Direction
from atlas.domain.models.instrument import Instrument
from atlas.infrastructure.persistence.decision_serializers import (
    confluence_from_dict,
    decision_to_cache_dict,
    news_status_from_dict,
    validation_from_dict,
)

DECISION_CACHE_TTL_SECONDS = 30


def _cache_key(symbol: str) -> str:
    return f"decision:{symbol.upper()}:latest"


def decision_from_cache_dict(data: dict) -> TradingDecision:
    """Rebuild a trading decision from cached JSON."""
    instrument = Instrument(
        id=UUID(data["instrument_id"]),
        symbol=data["symbol"],
        display_name=data["symbol"],
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )
    confluence = (
        confluence_from_dict(data["confluence_snapshot"], instrument)
        if data.get("confluence_snapshot")
        else None
    )
    validation = (
        validation_from_dict(data["validation_snapshot"], instrument)
        if data.get("validation_snapshot")
        else None
    )
    news = news_status_from_dict(data["news_status"]) if data.get("news_status") else None
    return TradingDecision(
        id=UUID(data["id"]),
        instrument=instrument,
        direction=Direction(data["direction"]),
        is_actionable=data["is_actionable"],
        confluence_score=Decimal(data["confluence_score"]),
        strategy_id=data["strategy_id"],
        reason=data["reason"],
        correlation_id=data["correlation_id"],
        decided_at=datetime.fromisoformat(data["decided_at"]),
        confluence_snapshot=confluence,
        validation_snapshot=validation,
        risk_snapshot=data.get("risk_snapshot"),
        news_status=news,
    )


class DecisionCache:
    """Cache latest decision per symbol."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def set_latest(self, decision: TradingDecision) -> None:
        """Store decision JSON."""
        await self._redis.setex(
            _cache_key(decision.instrument.symbol),
            DECISION_CACHE_TTL_SECONDS,
            json.dumps(decision_to_cache_dict(decision)),
        )

    async def get_latest(self, symbol: str) -> TradingDecision | None:
        """Retrieve cached decision or None."""
        raw = await self._redis.get(_cache_key(symbol))
        if not raw:
            return None
        return decision_from_cache_dict(json.loads(raw))
