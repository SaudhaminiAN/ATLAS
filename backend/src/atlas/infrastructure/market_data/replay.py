"""Database-backed bar replay for backtesting."""

import asyncio
from collections.abc import Iterator
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

    def iter_bars(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> Iterator[OHLCVBar]:
        """Iterate bars chronologically in [start, end]."""
        bars = asyncio.run(self._fetch_range(instrument, timeframe, start, end))
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

    async def _fetch_range(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVBar]:
        async with self._session_factory() as session:
            repo = OHLCVBarRepository(session)
            rows = await repo.get_history(instrument.id, timeframe, start, end, limit=100_000)
            return [bar_to_domain(r, instrument) for r in rows]

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
