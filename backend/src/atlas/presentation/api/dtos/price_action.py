"""Price action API DTOs."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class CandlePatternDTO(BaseModel):
    """Detected candlestick pattern."""

    pattern_type: str
    direction: str
    bar_index: int
    strength: Decimal
    at_key_level: bool


class PriceActionDTO(BaseModel):
    """Price action analysis snapshot."""

    symbol: str
    timeframe: str
    patterns: list[CandlePatternDTO]
    strongest_pattern: CandlePatternDTO | None
    computed_at: datetime
