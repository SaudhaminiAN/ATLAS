"""Risk management domain models (Spec 10)."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class RiskProfile:
    """Account risk configuration."""

    id: str
    account_balance: Decimal
    max_risk_percent: Decimal
    max_daily_loss_percent: Decimal
    max_open_positions: int
    min_rr: Decimal
    buffer_atr_multiplier: Decimal
    max_sl_distance_atr: Decimal
    min_sl_pips: int
    min_lot: Decimal
    lot_step: Decimal
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class RiskParameters:
    """Calculated trade risk parameters."""

    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    position_size: Decimal
    risk_amount: Decimal
    reward_risk_ratio: Decimal
    sl_basis: str


@dataclass(frozen=True, slots=True)
class RiskCheckResult:
    """Risk calculation outcome."""

    within_limits: bool
    parameters: RiskParameters | None
    breach_reason: str | None
