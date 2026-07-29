"""Market context API DTOs."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class MarketContextDTO(BaseModel):
    """Market context snapshot."""

    symbol: str
    primary_session: str
    active_sessions: list[str]
    volatility_regime: str
    spread_status: str
    structural_bias: str
    atr_value: Decimal
    atr_percentile: Decimal
    computed_at: datetime
