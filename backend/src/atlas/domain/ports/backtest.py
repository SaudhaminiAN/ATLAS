"""Backtesting port (Spec 16)."""

from typing import Protocol

from atlas.domain.models.backtest import BacktestConfig, BacktestResult


class BacktestRunnerProtocol(Protocol):
    """Run historical replay through the analysis pipeline."""

    async def run(self, config: BacktestConfig) -> BacktestResult: ...
