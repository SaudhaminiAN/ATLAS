"""Market context domain model."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from atlas.domain.models.enums import Bias, SpreadStatus, TradingSession, VolatilityRegime
from atlas.domain.models.instrument import Instrument


@dataclass(frozen=True, slots=True)
class MarketContext:
    """Classified trading environment for an instrument."""

    instrument: Instrument
    primary_session: TradingSession
    active_sessions: tuple[TradingSession, ...]
    volatility_regime: VolatilityRegime
    spread_status: SpreadStatus
    structural_bias: Bias
    atr_value: Decimal
    atr_percentile: Decimal
    computed_at: datetime
