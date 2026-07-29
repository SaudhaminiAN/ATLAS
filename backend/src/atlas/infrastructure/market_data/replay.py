"""Database-backed bar replay for backtesting."""

import asyncio
from collections.abc import AsyncIterator, Iterator
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from atlas.domain.models.enums import Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.infrastructure.persistence.repositories import (
    OHLCVBarRepository,
    bar_to_domain,
)


class DatabaseMarketDataReplay:
    """Replay bars from ohlcv_bars table (Spec 16)."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def fetch_range(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        *,
        limit: int = 100_000,
    ) -> list[OHLCVBar]:
        """Load bars chronologically in [start, end]."""
        async with self._session_factory() as session:
            repo = OHLCVBarRepository(session)
            rows = await repo.get_history(instrument.id, timeframe, start, end, limit=limit)
            return [bar_to_domain(r, instrument) for r in rows]

    async def iter_bars_async(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> AsyncIterator[OHLCVBar]:
        """Async iterator over historical bars (safe inside event loop)."""
        bars = await self.fetch_range(instrument, timeframe, start, end)
        for bar in bars:
            yield bar

    def iter_bars(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> Iterator[OHLCVBar]:
        """Iterate bars chronologically in [start, end] (sync CLI use only)."""
        bars = asyncio.run(self.fetch_range(instrument, timeframe, start, end))
        return iter(bars)

    def get_bars_up_to(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        as_of: datetime,
        limit: int,
    ) -> list[OHLCVBar]:
        """Return bars with open_time <= as_of (no look-ahead)."""
        return asyncio.run(self._fetch_up_to(instrument, timeframe, as_of, limit))

    async def _fetch_up_to(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        as_of: datetime,
        limit: int,
    ) -> list[OHLCVBar]:
        async with self._session_factory() as session:
            repo = OHLCVBarRepository(session)
            rows = await repo.get_bars_up_to(instrument.id, timeframe, as_of, limit)
            return [bar_to_domain(r, instrument) for r in rows]
