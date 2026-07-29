"""Technical analysis API DTOs."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class PriceLevelDTO(BaseModel):
    """Support or resistance level."""

    price: Decimal
    strength: Decimal
    level_type: str


class TechnicalAnalysisDTO(BaseModel):
    """Technical analysis snapshot."""

    symbol: str
    timeframe: str
    trend: str
    key_levels: list[PriceLevelDTO]
    nearest_support: Decimal | None
    nearest_resistance: Decimal | None
    indicator_context: dict[str, Decimal]
    bullish_context_score: Decimal
    bearish_context_score: Decimal
    computed_at: datetime
