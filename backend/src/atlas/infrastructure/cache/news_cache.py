"""Redis cache for upcoming economic events."""

import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from redis.asyncio import Redis

from atlas.domain.models.news import EconomicEvent, EventImpact

NEWS_CACHE_KEY = "news:events:upcoming"
NEWS_CACHE_TTL_SECONDS = 900


def _event_to_dict(event: EconomicEvent) -> dict:
    return {
        "id": str(event.id),
        "name": event.name,
        "currency": event.currency,
        "impact": event.impact.value,
        "scheduled_at": event.scheduled_at.isoformat(),
        "source": event.source,
        "actual": str(event.actual) if event.actual is not None else None,
        "forecast": str(event.forecast) if event.forecast is not None else None,
        "previous": str(event.previous) if event.previous is not None else None,
    }


def _event_from_dict(data: dict) -> EconomicEvent:
    return EconomicEvent(
        id=UUID(data["id"]),
        name=data["name"],
        currency=data["currency"],
        impact=EventImpact(data["impact"]),
        scheduled_at=datetime.fromisoformat(data["scheduled_at"]),
        source=data["source"],
        actual=Decimal(data["actual"]) if data.get("actual") else None,
        forecast=Decimal(data["forecast"]) if data.get("forecast") else None,
        previous=Decimal(data["previous"]) if data.get("previous") else None,
    )


class NewsEventCache:
    """Cache upcoming economic events."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def set_events(self, events: list[EconomicEvent]) -> None:
        """Store upcoming events with TTL."""
        payload = json.dumps([_event_to_dict(e) for e in events])
        await self._redis.setex(NEWS_CACHE_KEY, NEWS_CACHE_TTL_SECONDS, payload)

    async def get_events(self) -> list[EconomicEvent] | None:
        """Retrieve cached events or None."""
        raw = await self._redis.get(NEWS_CACHE_KEY)
        if not raw:
            return None
        return [_event_from_dict(item) for item in json.loads(raw)]
