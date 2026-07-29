"""Market context port."""

from decimal import Decimal
from typing import Protocol

from atlas.domain.models.instrument import Instrument
from atlas.domain.models.market_context import MarketContext
from atlas.domain.models.ohlcv import OHLCVBar


class MarketContextServiceProtocol(Protocol):
    """Compute market context from bar history."""

    def compute(
        self,
        instrument: Instrument,
        primary_bars: list[OHLCVBar],
        bias_timeframe_bars: list[OHLCVBar],
        spread: Decimal | None = None,
    ) -> MarketContext:
        """Derive context snapshot from bar data."""
        ...
