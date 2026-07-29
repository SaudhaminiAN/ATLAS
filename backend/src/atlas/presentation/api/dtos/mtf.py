"""MTF analysis API DTOs."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class TimeframeBiasDTO(BaseModel):
    """Per-timeframe bias."""

    timeframe: str
    bias: str
    confidence: Decimal
    trend_source: str
    key_levels: list[dict]


class MTFAnalysisDTO(BaseModel):
    """Multi-timeframe analysis snapshot."""

    symbol: str
    biases: list[TimeframeBiasDTO]
    alignment_score: Decimal
    dominant_bias: str
    has_conflict: bool
    distant_conflict: bool
    aligned: bool
    computed_at: datetime
