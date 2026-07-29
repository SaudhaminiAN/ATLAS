"""News filter service tests."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from atlas.application.news.service import NewsFilterService
from atlas.domain.events.base import DomainEvent
from atlas.domain.models.news import EconomicEvent, EventImpact
from atlas.domain.services.news_window import NewsFilterConfig
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus


def _event(name: str, scheduled_at: datetime) -> EconomicEvent:
    return EconomicEvent(
        id=uuid4(),
        name=name,
        currency="USD",
        impact=EventImpact.HIGH,
        scheduled_at=scheduled_at,
        source="test",
    )


class FakeProvider:
    def __init__(self, events: list[EconomicEvent]) -> None:
        self.events = events

    async def fetch_upcoming(self, start, end):
        return [e for e in self.events if start <= e.scheduled_at <= end]


class FakeNewsCache:
    def __init__(self) -> None:
        self.events: list[EconomicEvent] | None = None

    async def set_events(self, events):
        self.events = events

    async def get_events(self):
        return self.events


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class FakeRepo:
    def __init__(self, events: list[EconomicEvent]) -> None:
        self.events = events

    async def upsert_many(self, events):
        self.events = events

    async def list_between(self, start, end, impact=None):
        return [e for e in self.events if start <= e.scheduled_at <= end]


@pytest.fixture
def news_service(monkeypatch):
    event_time = datetime.now(UTC) + timedelta(hours=6)
    events = [_event("US CPI", event_time)]
    bus = InMemoryEventBus()
    captured: list[DomainEvent] = []
    bus.subscribe("news.window.blocked", lambda e: captured.append(e))
    bus.subscribe("news.window.cleared", lambda e: captured.append(e))

    def session_factory():
        return FakeSession()

    monkeypatch.setattr(
        "atlas.application.news.service.EconomicEventRepository",
        lambda session: FakeRepo(events),
    )

    service = NewsFilterService(
        session_factory=session_factory,  # type: ignore[arg-type]
        event_bus=bus,
        provider=FakeProvider(events),
        event_cache=FakeNewsCache(),  # type: ignore[arg-type]
        config=NewsFilterConfig(),
    )
    service._events = events
    return service, event_time, captured


def test_check_uses_in_memory_events(news_service) -> None:
    service, event_time, _ = news_service
    status = service.check(event_time)
    assert status.is_blocked is True


@pytest.mark.asyncio
async def test_refresh_calendar_updates_events(news_service) -> None:
    service, _, _ = news_service
    refreshed = await service.refresh_calendar()
    assert len(refreshed) >= 1
    assert service._last_sync_at is not None


def test_emit_window_blocked_event(news_service) -> None:
    service, event_time, captured = news_service
    service.emit_window_transitions(event_time)
    assert len(captured) == 1
    assert captured[0].event_type == "news.window.blocked"


def test_emit_window_cleared_event(news_service) -> None:
    service, event_time, captured = news_service
    service._last_blocked = True
    service.emit_window_transitions(event_time - timedelta(hours=2))
    assert len(captured) == 1
    assert captured[0].event_type == "news.window.cleared"
