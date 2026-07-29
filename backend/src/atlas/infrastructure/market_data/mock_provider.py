"""Mock market data provider for development and tests."""

import asyncio
import random
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from atlas.domain.models.enums import Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.services.bar_validation import TIMEFRAME_MINUTES, to_utc


class MockMarketDataProvider:
    """Generates synthetic XAUUSD OHLCV bars."""

    def __init__(
        self,
        base_price: Decimal = Decimal("2350.00"),
        interval_seconds: float = 2.0,
    ) -> None:
        self._base_price = base_price
        self._interval_seconds = interval_seconds
        self._price = base_price

    async def fetch_bars(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVBar]:
        """Generate historical bars between start and end."""
        bars: list[OHLCVBar] = []
        minutes = TIMEFRAME_MINUTES[timeframe]
        current = self._align_to_timeframe(start, timeframe)
        end_utc = self._align_to_timeframe(end, timeframe)
        price = self._base_price

        while current <= end_utc:
            bar, price = self._make_bar(instrument, timeframe, current, price)
            bars.append(bar)
            current += timedelta(minutes=minutes)

        return bars

    async def subscribe_bars(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
    ) -> AsyncIterator[OHLCVBar]:
        """Yield closed bars at interval (simulated stream)."""
        while True:
            now = datetime.now(UTC)
            aligned = self._align_to_timeframe(now, timeframe)
            bar, self._price = self._make_bar(instrument, timeframe, aligned, self._price)
            yield bar
            await asyncio.sleep(self._interval_seconds)

    def _align_to_timeframe(self, dt: datetime, timeframe: Timeframe) -> datetime:
        """Align datetime down to timeframe boundary."""
        dt = to_utc(dt).replace(second=0, microsecond=0)
        if timeframe == Timeframe.M5:
            dt = dt.replace(minute=(dt.minute // 5) * 5)
        elif timeframe == Timeframe.M15:
            dt = dt.replace(minute=(dt.minute // 15) * 15)
        elif timeframe == Timeframe.M30:
            dt = dt.replace(minute=(dt.minute // 30) * 30)
        elif timeframe == Timeframe.H1:
            dt = dt.replace(minute=0)
        elif timeframe == Timeframe.H4:
            dt = dt.replace(minute=0, hour=(dt.hour // 4) * 4)
        elif timeframe == Timeframe.D1:
            dt = dt.replace(minute=0, hour=0)
        return dt

    def _make_bar(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        open_time: datetime,
        price: Decimal,
    ) -> tuple[OHLCVBar, Decimal]:
        """Create a single synthetic bar."""
        delta = Decimal(str(random.uniform(-2.0, 2.0)))
        open_p = price
        close_p = price + delta
        high_p = max(open_p, close_p) + Decimal(str(random.uniform(0, 1.5)))
        low_p = min(open_p, close_p) - Decimal(str(random.uniform(0, 1.5)))
        bar = OHLCVBar(
            instrument=instrument,
            timeframe=timeframe,
            open_time=open_time,
            open=open_p,
            high=high_p,
            low=low_p,
            close=close_p,
            volume=Decimal(str(random.randint(100, 5000))),
        )
        return bar, close_p
