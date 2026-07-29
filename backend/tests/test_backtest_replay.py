"""Pipeline replay mode tests."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from atlas.application.pipeline.orchestrator import AnalysisPipelineOrchestrator, PipelineConfig
from atlas.domain.models.backtest import BacktestConfig
from atlas.domain.models.enums import Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.pipeline import PipelineStatus
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def _bar(open_time: datetime) -> OHLCVBar:
    instrument = _instrument()
    return OHLCVBar(
        instrument=instrument,
        timeframe=Timeframe.M15,
        open_time=open_time,
        open=Decimal("2350"),
        high=Decimal("2351"),
        low=Decimal("2349"),
        close=Decimal("2350"),
        volume=Decimal("1000"),
    )


@pytest.mark.asyncio
async def test_run_replay_skips_dedupe_and_persists_nothing() -> None:
    instrument = _instrument()
    bar = OHLCVBar(
        instrument=instrument,
        timeframe=Timeframe.M15,
        open_time=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        open=Decimal("2350"),
        high=Decimal("2351"),
        low=Decimal("2349"),
        close=Decimal("2350"),
        volume=Decimal("1000"),
    )

    orchestrator = MagicMock(spec=AnalysisPipelineOrchestrator)
    orchestrator.config = PipelineConfig(primary_timeframe=Timeframe.M15)
    orchestrator.run = AsyncMock(
        return_value=MagicMock(status=PipelineStatus.COMPLETED, stage_results={})
    )

    from atlas.application.pipeline import orchestrator as orchestrator_module

    real_run_replay = orchestrator_module.AnalysisPipelineOrchestrator.run_replay
    orchestrator.run_replay = real_run_replay.__get__(orchestrator, AnalysisPipelineOrchestrator)

    async def bar_iter():
        yield bar

    config = BacktestConfig(
        symbol="XAUUSD",
        timeframe=Timeframe.M15,
        start=bar.open_time,
        end=bar.open_time,
    )
    runs = await orchestrator.run_replay(instrument, bar_iter(), config)

    assert len(runs) == 1
    orchestrator.run.assert_awaited_once()
    call_kwargs = orchestrator.run.await_args.kwargs
    assert call_kwargs["replay"].skip_dedupe is True
    assert call_kwargs["replay"].persist_decisions is False
    assert call_kwargs["replay"].publish_events is False
