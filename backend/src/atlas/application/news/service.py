"""News filter application service."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from atlas.domain.events.base import DomainEvent
from atlas.domain.models.news import EconomicEvent, NewsFilterStatus
from atlas.domain.ports.event_bus import EventBusProtocol
from atlas.domain.ports.news import NewsCalendarProviderProtocol
from atlas.domain.services.news_window import NewsFilterConfig, compute_news_status
from atlas.infrastructure.cache.news_cache import NewsEventCache
from atlas.infrastructure.persistence.repositories import EconomicEventRepository

logger = structlog.get_logger(__name__)


@dataclass
class NewsFilterService:
    """Sync calendar data and evaluate news windows."""

    session_factory: async_sessionmaker[AsyncSession]
    event_bus: EventBusProtocol
    provider: NewsCalendarProviderProtocol
    event_cache: NewsEventCache
    config: NewsFilterConfig = field(default_factory=NewsFilterConfig)
    stale_warning_minutes: int = 60
    _events: list[EconomicEvent] = field(default_factory=list, repr=False)
    _last_sync_at: datetime | None = field(default=None, repr=False)
    _last_blocked: bool = field(default=False, repr=False)

    def check(self, as_of: datetime) -> NewsFilterStatus:
        """Evaluate news filter status using synced events."""
        self._warn_if_stale()
        return compute_news_status(self._events, as_of, self.config)

    async def refresh_calendar(self, *, horizon_hours: int = 48) -> list[EconomicEvent]:
        """Fetch from provider, persist, cache, and update in-memory events."""
        now = datetime.now(UTC)
        end = now + timedelta(hours=horizon_hours)
        fetched = await self.provider.fetch_upcoming(now - timedelta(hours=1), end)

        async with self.session_factory() as session:
            repo = EconomicEventRepository(session)
            await repo.upsert_many(fetched)
            stored = await repo.list_between(now - timedelta(hours=1), end)

        self._events = stored
        self._last_sync_at = now
        await self.event_cache.set_events(stored)
        logger.info("news_calendar_refreshed", event_count=len(stored))
        return stored

    async def load_events(self) -> None:
        """Load events from cache or database into memory."""
        cached = await self.event_cache.get_events()
        if cached is not None:
            self._events = cached
            return

        now = datetime.now(UTC)
        end = now + timedelta(hours=48)
        async with self.session_factory() as session:
            repo = EconomicEventRepository(session)
            self._events = await repo.list_between(now - timedelta(hours=1), end)

    async def get_upcoming(self, hours: int = 24) -> list[EconomicEvent]:
        """Return upcoming high-impact events."""
        now = datetime.now(UTC)
        end = now + timedelta(hours=hours)
        return [
            e
            for e in self._events
            if e.scheduled_at >= now and e.scheduled_at <= end
        ]

    def emit_window_transitions(self, as_of: datetime | None = None) -> None:
        """Publish blocked/cleared events when window state changes."""
        current = self.check(as_of or datetime.now(UTC))
        if current.is_blocked and not self._last_blocked:
            self.event_bus.publish(
                DomainEvent(
                    event_type="news.window.blocked",
                    correlation_id="news-filter",
                    payload={
                        "as_of": current.as_of.isoformat(),
                        "next_event": (
                            {
                                "name": current.next_event.name,
                                "scheduled_at": current.next_event.scheduled_at.isoformat(),
                            }
                            if current.next_event
                            else None
                        ),
                    },
                )
            )
        elif not current.is_blocked and self._last_blocked:
            self.event_bus.publish(
                DomainEvent(
                    event_type="news.window.cleared",
                    correlation_id="news-filter",
                    payload={"as_of": current.as_of.isoformat()},
                )
            )
        self._last_blocked = current.is_blocked

    def _warn_if_stale(self) -> None:
        if self._last_sync_at is None:
            return
        age = datetime.now(UTC) - self._last_sync_at
        if age > timedelta(minutes=self.stale_warning_minutes):
            logger.warning(
                "news_calendar_stale",
                minutes_stale=int(age.total_seconds() // 60),
            )
