"""Risk management port (Spec 10)."""

from decimal import Decimal
from typing import Protocol

from atlas.domain.models.enums import Direction
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.risk import RiskCheckResult, RiskProfile
from atlas.domain.models.smc import SMCAnalysisResult
from atlas.domain.models.technical import TechnicalAnalysisResult


class RiskManagementServiceProtocol(Protocol):
    """Calculate position size, SL/TP, and enforce limits."""

    def calculate(
        self,
        direction: Direction,
        entry_price: Decimal,
        technical: TechnicalAnalysisResult,
        smc: SMCAnalysisResult,
        atr: Decimal,
        instrument: Instrument,
        profile: RiskProfile,
        *,
        open_positions_count: int = 0,
        daily_pnl: Decimal = Decimal("0"),
    ) -> RiskCheckResult: ...
