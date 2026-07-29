"""Mock economic calendar provider for development and CI."""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import NAMESPACE_DNS, UUID, uuid5

from atlas.domain.models.news import EconomicEvent, EventImpact
from atlas.domain.services.bar_validation import to_utc

MOCK_EVENTS = (
    ("US Non-Farm Payrolls", "USD"),
    ("US CPI", "USD"),
    ("FOMC Rate Decision", "USD"),
    ("US PPI", "USD"),
)


def _event_id(name: str, scheduled_at: datetime) -> UUID:
    return uuid5(NAMESPACE_DNS, f"{name}:{scheduled_at.isoformat()}")


class MockNewsCalendarProvider:
    """Generates synthetic high-impact USD events affecting XAUUSD."""

    def __init__(self, horizon_hours: int = 48) -> None:
        self._horizon_hours = horizon_hours

    async def fetch_upcoming(
        self,
        start: datetime,
        end: datetime,
    ) -> list[EconomicEvent]:
        """Return recurring mock events on weekday mornings UTC."""
        start_utc = to_utc(start)
        end_utc = to_utc(end)
        events: list[EconomicEvent] = []
        current = start_utc.replace(hour=0, minute=0, second=0, microsecond=0)

        while current <= end_utc:
            if current.weekday() < 5:
                for hour_offset, (name, currency) in enumerate(MOCK_EVENTS):
                    scheduled = current.replace(hour=12 + hour_offset, minute=30)
                    if start_utc <= scheduled <= end_utc:
                        events.append(
                            EconomicEvent(
                                id=_event_id(name, scheduled),
                                name=name,
                                currency=currency,
                                impact=EventImpact.HIGH,
                                scheduled_at=scheduled,
                                source="mock",
                                forecast=Decimal("0"),
                                previous=Decimal("0"),
                            )
                        )
            current += timedelta(days=1)

        return sorted(events, key=lambda e: e.scheduled_at)
