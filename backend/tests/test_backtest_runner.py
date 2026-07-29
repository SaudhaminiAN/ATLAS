"""Backtest runner tests (Spec 16)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from atlas.application.backtesting.report import build_backtest_result
from atlas.application.backtesting.runner import BacktestRunner
from atlas.application.pipeline.orchestrator import AnalysisPipelineOrchestrator, PipelineConfig
from atlas.domain.models.backtest import BacktestConfig
from atlas.domain.models.confluence import ConfluenceResult, EvidenceItem
from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.enums import Direction, Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.pipeline import PipelineRun, PipelineStatus
from atlas.domain.models.validation import ValidationResult


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def _bar(instrument: Instrument, index: int) -> OHLCVBar:
    open_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC) + timedelta(minutes=15 * index)
    price = Decimal("2350") + Decimal(index)
    return OHLCVBar(
        instrument=instrument,
        timeframe=Timeframe.M15,
        open_time=open_time,
        open=price,
        high=price + Decimal("1"),
        low=price - Decimal("1"),
        close=price,
        volume=Decimal("1000"),
    )


def _make_bars(instrument: Instrument, count: int) -> list[OHLCVBar]:
    return [_bar(instrument, i) for i in range(count)]


def _wait_decision(instrument: Instrument, open_time: datetime, reason: str) -> TradingDecision:
    confluence = ConfluenceResult(
        instrument=instrument,
        suggested_direction=Direction.WAIT,
        total_score=Decimal("0"),
        raw_score=Decimal("0"),
        bullish_raw=Decimal("0"),
        bearish_raw=Decimal("0"),
        news_penalty=Decimal("0"),
        module_scores=(),
        evidence=(
            EvidenceItem(
                source="mtf_alignment",
                direction=Direction.WAIT,
                weight=Decimal("0.25"),
                score=Decimal("0"),
                weighted_contribution=Decimal("0"),
                description="neutral",
            ),
        ),
        evidence_count=1,
        has_conflict=False,
        strategy_profile_id="test",
        computed_at=open_time,
    )
    validation = ValidationResult(
        instrument=instrument,
        direction=Direction.WAIT,
        is_valid=False,
        rules=(),
        failed_rules=("direction_check",),
        strategy_profile_id="test",
        validated_at=open_time,
    )
    return TradingDecision(
        id=uuid4(),
        instrument=instrument,
        direction=Direction.WAIT,
        is_actionable=False,
        confluence_score=Decimal("0"),
        strategy_id="test",
        reason=reason,
        correlation_id=f"replay-XAUUSD-{open_time.isoformat()}",
        decided_at=open_time,
        confluence_snapshot=confluence,
        validation_snapshot=validation,
    )


@pytest.mark.asyncio
async def test_backtest_runner_replays_bars_chronologically() -> None:
    instrument = _instrument()
    bars = _make_bars(instrument, 5)
    config = BacktestConfig(
        symbol="XAUUSD",
        timeframe=Timeframe.M15,
        start=bars[0].open_time,
        end=bars[-1].open_time,
    )

    seen_times: list[datetime] = []

    async def run_replay(inst, bar_iter, cfg):
        runs = []
        async for bar in bar_iter:
            seen_times.append(bar.open_time)
            runs.append(
                PipelineRun(
                    correlation_id=f"replay-{bar.open_time.isoformat()}",
                    instrument=inst,
                    trigger_timeframe=bar.timeframe,
                    trigger_bar_time=bar.open_time,
                    status=PipelineStatus.COMPLETED,
                )
            )
        return runs

    pipeline = MagicMock(spec=AnalysisPipelineOrchestrator)
    pipeline.run_replay = run_replay
    pipeline.decision_engine = MagicMock()
    pipeline.decision_engine.emit = AsyncMock()

    market_data = MagicMock()
    market_data.get_instrument = AsyncMock(return_value=instrument)

    replay = MagicMock()

    async def iter_bars_async(inst, tf, start, end):
        for bar in bars:
            yield bar

    replay.iter_bars_async = iter_bars_async

    runner = BacktestRunner(
        pipeline=pipeline,
        market_data_service=market_data,
        market_data_replay=replay,
    )
    result = await runner.run(config)

    assert seen_times == [bar.open_time for bar in bars]
    assert result.bars_processed == 5
    assert result.completed_runs == 5


@pytest.mark.asyncio
async def test_no_lookahead_spy_on_get_recent_bars() -> None:
    """Assert market data queries never request bars after trigger time."""
    instrument = _instrument()
    bars = _make_bars(instrument, 3)
    violations: list[tuple[datetime, datetime]] = []

    market_data = MagicMock()

    async def get_recent_bars(inst, timeframe, limit, as_of):
        filtered = [bar for bar in bars if bar.open_time <= as_of][-limit:]
        for bar in filtered:
            if bar.open_time > as_of:
                violations.append((as_of, bar.open_time))
        return filtered

    market_data.get_recent_bars = get_recent_bars
    market_data.get_instrument = AsyncMock(return_value=instrument)

    pipeline = MagicMock(spec=AnalysisPipelineOrchestrator)

    async def run_replay(inst, bar_iter, cfg):
        runs = []
        async for bar in bar_iter:
            await market_data.get_recent_bars(
                inst,
                Timeframe.M15,
                limit=120,
                as_of=bar.open_time,
            )
            runs.append(
                PipelineRun(
                    correlation_id="x",
                    instrument=inst,
                    trigger_timeframe=bar.timeframe,
                    trigger_bar_time=bar.open_time,
                    status=PipelineStatus.COMPLETED,
                )
            )
        return runs

    pipeline.run_replay = run_replay
    pipeline.decision_engine = MagicMock()
    pipeline.decision_engine.emit = AsyncMock()

    replay = MagicMock()

    async def iter_bars_async(inst, tf, start, end):
        for bar in bars:
            yield bar

    replay.iter_bars_async = iter_bars_async

    runner = BacktestRunner(
        pipeline=pipeline,
        market_data_service=market_data,
        market_data_replay=replay,
    )
    config = BacktestConfig(
        symbol="XAUUSD",
        timeframe=Timeframe.M15,
        start=bars[0].open_time,
        end=bars[-1].open_time,
    )
    await runner.run(config)
    assert violations == []


def test_build_backtest_result_golden_100_bars() -> None:
    """Golden-style aggregation over 100 synthetic decisions."""
    instrument = _instrument()
    decisions = [
        _wait_decision(instrument, _bar(instrument, i).open_time, "Validation failed: direction_check")
        for i in range(100)
    ]
    runs = [
        PipelineRun(
            correlation_id=f"r-{i}",
            instrument=instrument,
            trigger_timeframe=Timeframe.M15,
            trigger_bar_time=decisions[i].decided_at,
            status=PipelineStatus.COMPLETED,
        )
        for i in range(100)
    ]
    config = BacktestConfig(
        symbol="XAUUSD",
        timeframe=Timeframe.M15,
        start=decisions[0].decided_at,
        end=decisions[-1].decided_at,
    )
    result = build_backtest_result(runs, config, decisions, duration_ms=1500)

    assert result.bars_processed == 100
    assert result.completed_runs == 100
    assert len(result.decision_counts) == 1
    assert result.decision_counts[0].direction == Direction.WAIT
    assert result.decision_counts[0].count == 100
    assert result.wait_reasons[0][1] == 100
    assert len(result.module_accuracy) == 1
    assert result.module_accuracy[0].source == "mtf_alignment"
    assert result.module_accuracy[0].appearances == 100
