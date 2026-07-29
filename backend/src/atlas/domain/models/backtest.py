"""Backtesting domain models (Spec 16)."""

from dataclasses import dataclass
from datetime import datetime

from atlas.domain.models.enums import Direction, Timeframe


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    """Configuration for a historical replay run."""

    symbol: str
    timeframe: Timeframe
    start: datetime
    end: datetime
    persist_decisions: bool = False
    persist_pipeline_runs: bool = False
    risk_enabled: bool = False


@dataclass(frozen=True, slots=True)
class DecisionSummary:
    """Aggregate decision counts by direction."""

    direction: Direction
    count: int


@dataclass(frozen=True, slots=True)
class ModuleAccuracySummary:
    """Per-evidence-source stats from replay decisions."""

    source: str
    appearances: int
    actionable_appearances: int


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Report produced after a backtest replay."""

    symbol: str
    timeframe: Timeframe
    start: datetime
    end: datetime
    bars_processed: int
    pipeline_runs: int
    completed_runs: int
    skipped_runs: int
    failed_runs: int
    decision_counts: tuple[DecisionSummary, ...]
    wait_reasons: tuple[tuple[str, int], ...]
    module_accuracy: tuple[ModuleAccuracySummary, ...]
    duration_ms: int
