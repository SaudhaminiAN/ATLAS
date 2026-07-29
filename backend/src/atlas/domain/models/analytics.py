"""Analytics domain models (Spec 14)."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class AnalyticsFilters:
    """Date and profile filters for analytics queries."""

    symbol: str | None = None
    strategy_profile_id: str | None = None
    start: datetime | None = None
    end: datetime | None = None


@dataclass(frozen=True, slots=True)
class WaitReasonCount:
    """Grouped WAIT reason with occurrence count."""

    reason: str
    count: int


@dataclass(frozen=True, slots=True)
class DecisionStats:
    """Decision-level analytics over a date range."""

    total_decisions: int
    wait_count: int
    buy_count: int
    sell_count: int
    actionable_count: int
    wait_rate: Decimal
    actionable_rate: Decimal
    top_wait_reasons: tuple[WaitReasonCount, ...]


@dataclass(frozen=True, slots=True)
class ModuleAccuracy:
    """Per-evidence-source accuracy metrics."""

    source: str
    appearances: int
    true_positive: int
    false_signal: int
    neutral_wait: int
    true_positive_rate: Decimal
    false_signal_rate: Decimal


@dataclass(frozen=True, slots=True)
class PerformanceSummary:
    """Trade performance metrics (zeroed when no trades exist)."""

    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    profit_factor: Decimal
    total_pnl: Decimal
    max_drawdown: Decimal


@dataclass(frozen=True, slots=True)
class EquityPoint:
    """Point on the equity curve."""

    timestamp: datetime
    equity: Decimal
