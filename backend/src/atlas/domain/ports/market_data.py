"""Market data port interfaces."""

from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from typing import Protocol

from atlas.domain.models.enums import Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import IngestResult, OHLCVBar


class MarketDataProviderProtocol(Protocol):
    """External market data source adapter."""

    async def fetch_bars(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVBar]: ...

    async def subscribe_bars(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
    ) -> AsyncIterator[OHLCVBar]: ...


class MarketDataReplayProtocol(Protocol):
    """Historical bar replay for backtesting (Spec 16)."""

    def iter_bars(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> Iterator[OHLCVBar]: ...

    def get_bars_up_to(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        as_of: datetime,
        limit: int,
    ) -> list[OHLCVBar]: ...


class MarketDataServiceProtocol(Protocol):
    """Market data ingestion and query service."""

    async def ingest_bar(self, bar: OHLCVBar, *, is_closed: bool = True) -> IngestResult: ...

    async def get_latest(self, instrument: Instrument, timeframe: Timeframe) -> OHLCVBar | None: ...

    async def get_history(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        limit: int = 500,
    ) -> list[OHLCVBar]: ...
