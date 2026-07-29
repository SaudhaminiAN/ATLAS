"""Execution domain models (Spec 11)."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from atlas.domain.models.enums import Direction
from atlas.domain.models.instrument import Instrument


class TradeStatus(StrEnum):
    """Trade lifecycle status."""

    OPEN = "open"
    PARTIAL = "partial"
    CLOSED = "closed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class OrderStatus(StrEnum):
    """Order submission outcome."""

    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class OrderRequest:
    """Order to submit to an execution provider."""

    decision_id: UUID
    instrument: Instrument
    direction: Direction
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    position_size: Decimal
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class OrderResult:
    """Result from order submission."""

    status: OrderStatus
    order_id: str | None
    fill_price: Decimal | None
    rejection_reason: str | None


@dataclass(frozen=True, slots=True)
class Trade:
    """Persisted trade record."""

    id: UUID
    decision_id: UUID
    instrument: Instrument
    direction: Direction
    status: TradeStatus
    entry_price: Decimal
    fill_price: Decimal | None
    stop_loss: Decimal
    take_profit: Decimal
    position_size: Decimal
    execution_mode: str
    rejection_reason: str | None
    opened_at: datetime
    closed_at: datetime | None
    realized_pnl: Decimal | None
    initial_stop_loss: Decimal | None = None
    remaining_size: Decimal | None = None
    partial_realized_pnl: Decimal = Decimal("0")
    breakeven_applied: bool = False
    partial_exit_applied: bool = False


@dataclass(frozen=True, slots=True)
class TradeEvent:
    """Append-only trade audit event."""

    id: UUID
    trade_id: UUID
    event_type: str
    payload: dict
    created_at: datetime
