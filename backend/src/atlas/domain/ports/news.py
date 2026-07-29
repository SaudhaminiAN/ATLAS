"""News filter ports."""

from datetime import datetime
from typing import Protocol

from atlas.domain.models.news import EconomicEvent, NewsFilterStatus


class NewsCalendarProviderProtocol(Protocol):
    """External economic calendar provider."""

    async def fetch_upcoming(
        self,
        start: datetime,
        end: datetime,
    ) -> list[EconomicEvent]:
        """Fetch events scheduled between start and end (UTC)."""
        ...


class NewsFilterServiceProtocol(Protocol):
    """News filter evaluation service."""

    def check(self, as_of: datetime) -> NewsFilterStatus:
        """Evaluate news filter status at a point in time."""
        ...
