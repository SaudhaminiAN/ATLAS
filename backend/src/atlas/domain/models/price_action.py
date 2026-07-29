"""Price action domain models."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from atlas.domain.models.enums import Bias, Timeframe
from atlas.domain.models.instrument import Instrument


@dataclass(frozen=True, slots=True)
class CandlePattern:
    """Detected candlestick pattern on a closed bar."""

    pattern_type: str
    direction: Bias
    bar_index: int
    strength: Decimal
    at_key_level: bool


@dataclass(frozen=True, slots=True)
class PriceActionResult:
    """Price action analysis output per timeframe."""

    instrument: Instrument
    timeframe: Timeframe
    patterns: tuple[CandlePattern, ...]
    strongest_pattern: CandlePattern | None
    computed_at: datetime
