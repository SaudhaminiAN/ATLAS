"""Backtest runner service (Spec 16)."""

import time
from dataclasses import dataclass

import structlog

from atlas.application.backtesting.report import build_backtest_result
from atlas.application.market_data.service import MarketDataService
from atlas.application.pipeline.orchestrator import AnalysisPipelineOrchestrator
from atlas.domain.models.backtest import BacktestConfig, BacktestResult
from atlas.domain.models.decision import TradingDecision
from atlas.infrastructure.market_data.replay import DatabaseMarketDataReplay

logger = structlog.get_logger(__name__)


@dataclass
class BacktestRunner:
    """Replay historical bars through the analysis pipeline."""

    pipeline: AnalysisPipelineOrchestrator
    market_data_service: MarketDataService
    market_data_replay: DatabaseMarketDataReplay

    async def run(self, config: BacktestConfig) -> BacktestResult:
        """Execute chronological replay and return aggregated report."""
        instrument = await self.market_data_service.get_instrument(config.symbol)
        if instrument is None:
            msg = f"Unknown instrument: {config.symbol}"
            raise ValueError(msg)

        collected: list[TradingDecision] = []
        original_emit = self.pipeline.decision_engine.emit

        async def collecting_emit(
            decision: TradingDecision,
            *,
            persist: bool = True,
            publish: bool = True,
        ) -> None:
            collected.append(decision)
            await original_emit(decision, persist=persist, publish=publish)

        self.pipeline.decision_engine.emit = collecting_emit  # type: ignore[method-assign]
        started = time.perf_counter()
        try:
            bar_iterator = self.market_data_replay.iter_bars_async(
                instrument,
                config.timeframe,
                config.start,
                config.end,
            )
            runs = await self.pipeline.run_replay(instrument, bar_iterator, config)
        finally:
            self.pipeline.decision_engine.emit = original_emit  # type: ignore[method-assign]

        duration_ms = int((time.perf_counter() - started) * 1000)
        result = build_backtest_result(
            runs,
            config,
            collected,
            duration_ms=duration_ms,
        )
        logger.info(
            "backtest_completed",
            symbol=config.symbol,
            bars=result.bars_processed,
            completed=result.completed_runs,
            duration_ms=duration_ms,
        )
        return result
