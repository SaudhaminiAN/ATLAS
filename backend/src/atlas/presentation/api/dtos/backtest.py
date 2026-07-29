"""Backtest API DTOs."""

from datetime import datetime

from pydantic import BaseModel, Field


class DecisionSummaryDTO(BaseModel):
    direction: str
    count: int


class ModuleAccuracySummaryDTO(BaseModel):
    source: str
    appearances: int
    actionable_appearances: int


class BacktestResultDTO(BaseModel):
    symbol: str
    timeframe: str
    start: datetime
    end: datetime
    bars_processed: int
    pipeline_runs: int
    completed_runs: int
    skipped_runs: int
    failed_runs: int
    decision_counts: list[DecisionSummaryDTO]
    wait_reasons: list[tuple[str, int]]
    module_accuracy: list[ModuleAccuracySummaryDTO]
    duration_ms: int


class BacktestRunRequestDTO(BaseModel):
    symbol: str = Field(default="XAUUSD")
    timeframe: str = Field(default="M15")
    start: datetime
    end: datetime
    persist_decisions: bool = False
    persist_pipeline_runs: bool = False
    risk_enabled: bool = False
