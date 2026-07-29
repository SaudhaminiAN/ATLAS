"""MTF analysis domain models."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from atlas.domain.models.enums import Bias, Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.price_level import PriceLevel


@dataclass(frozen=True, slots=True)
class TimeframeBias:
    """Directional bias for a single timeframe."""

    timeframe: Timeframe
    bias: Bias
    confidence: Decimal
    trend_source: str
    key_levels: tuple[PriceLevel, ...]


@dataclass(frozen=True, slots=True)
class MTFAnalysis:
    """Multi-timeframe alignment result."""

    instrument: Instrument
    biases: tuple[TimeframeBias, ...]
    alignment_score: Decimal
    dominant_bias: Bias
    has_conflict: bool
    distant_conflict: bool
    aligned: bool
    computed_at: datetime
