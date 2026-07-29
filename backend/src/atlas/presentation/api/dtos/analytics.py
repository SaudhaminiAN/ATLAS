"""Analytics API DTOs."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class WaitReasonCountDTO(BaseModel):
    reason: str
    count: int


class DecisionStatsDTO(BaseModel):
    total_decisions: int
    wait_count: int
    buy_count: int
    sell_count: int
    actionable_count: int
    wait_rate: Decimal
    actionable_rate: Decimal
    top_wait_reasons: list[WaitReasonCountDTO]


class ModuleAccuracyDTO(BaseModel):
    source: str
    appearances: int
    true_positive: int
    false_signal: int
    neutral_wait: int
    true_positive_rate: Decimal
    false_signal_rate: Decimal


class PerformanceSummaryDTO(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    profit_factor: Decimal
    total_pnl: Decimal
    max_drawdown: Decimal


class EquityPointDTO(BaseModel):
    timestamp: datetime
    equity: Decimal
