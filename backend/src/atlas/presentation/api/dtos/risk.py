"""Risk API DTOs."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class RiskProfileDTO(BaseModel):
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


class UpdateRiskProfileRequest(BaseModel):
    account_balance: Decimal | None = None
    max_risk_percent: Decimal | None = Field(default=None, ge=0, le=100)
    max_daily_loss_percent: Decimal | None = Field(default=None, ge=0, le=100)
    max_open_positions: int | None = Field(default=None, ge=1)
    min_rr: Decimal | None = Field(default=None, ge=1)
    buffer_atr_multiplier: Decimal | None = None
    max_sl_distance_atr: Decimal | None = None
    min_sl_pips: int | None = Field(default=None, ge=1)
    min_lot: Decimal | None = None
    lot_step: Decimal | None = None
