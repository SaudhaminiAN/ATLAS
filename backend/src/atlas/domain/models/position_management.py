"""Position management domain models (Spec 12)."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from atlas.domain.models.enums import Direction


class ActionType(StrEnum):
    """Position management action."""

    BREAKEVEN = "breakeven"
    TRAIL_SL = "trail_sl"
    PARTIAL_CLOSE = "partial_close"
    CLOSE = "close"


class PositionStatus(StrEnum):
    """Open position lifecycle."""

    OPEN = "open"
    PARTIAL = "partial"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class PositionManagementConfig:
    """Rules for managing open positions."""

    breakeven_at_r: Decimal
    trailing_enabled: bool
    trailing_method: str
    trailing_atr_multiplier: Decimal
    partial_exit_enabled: bool
    partial_exit_percent: Decimal
    partial_exit_at_r: Decimal
    tp2_at_r: Decimal
    min_lot: Decimal


@dataclass(frozen=True, slots=True)
class PositionState:
    """Mutable snapshot used during bar evaluation."""

    trade_id: UUID
    direction: Direction
    entry_price: Decimal
    initial_stop_loss: Decimal
    current_sl: Decimal
    current_tp: Decimal
    position_size: Decimal
    remaining_size: Decimal
    partial_realized_pnl: Decimal
    breakeven_applied: bool
    partial_exit_applied: bool
    status: PositionStatus

    @property
    def risk_distance(self) -> Decimal:
        return abs(self.entry_price - self.initial_stop_loss)


@dataclass(frozen=True, slots=True)
class PositionAction:
    """Recorded management action."""

    trade_id: UUID
    action_type: ActionType
    old_sl: Decimal | None
    new_sl: Decimal | None
    closed_size: Decimal | None
    close_price: Decimal | None
    reason: str
    bar_time: datetime
    realized_pnl_delta: Decimal | None = None
