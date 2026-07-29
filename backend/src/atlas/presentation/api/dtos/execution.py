"""Execution API DTOs."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class TradeDTO(BaseModel):
    id: str
    decision_id: str
    symbol: str
    direction: str
    status: str
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
    remaining_size: Decimal | None = None
    partial_realized_pnl: Decimal | None = None


class CloseTradeRequest(BaseModel):
    reason: str = "manual"
