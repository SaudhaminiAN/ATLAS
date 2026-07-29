"""Technical analysis domain models."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from atlas.domain.models.enums import Timeframe, Trend
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.price_level import PriceLevel


@dataclass(frozen=True, slots=True)
class TechnicalAnalysisResult:
    """Technical analysis output per timeframe."""

    instrument: Instrument
    timeframe: Timeframe
    trend: Trend
    key_levels: tuple[PriceLevel, ...]
    nearest_support: Decimal | None
    nearest_resistance: Decimal | None
    indicator_context: dict[str, Decimal]
    bullish_context_score: Decimal
    bearish_context_score: Decimal
    computed_at: datetime
