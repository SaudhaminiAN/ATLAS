"""Market data API DTOs."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class InstrumentDTO(BaseModel):
    """Instrument response."""

    symbol: str
    display_name: str
    pip_size: Decimal
    lot_size: Decimal
    is_active: bool


class OHLCVBarDTO(BaseModel):
    """OHLCV bar response."""

    symbol: str
    timeframe: str
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    is_outlier: bool = False
    quality_flags: list[str] = Field(default_factory=list)
