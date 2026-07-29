"""Pipeline orchestrator tests."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from atlas.application.decision.service import DecisionEngineService
from atlas.application.pipeline.orchestrator import AnalysisPipelineOrchestrator, PipelineConfig
from atlas.domain.models.confluence import ConfluenceResult
from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.enums import Bias, Direction, Timeframe, Trend
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.market_context import MarketContext
from atlas.domain.models.mtf import MTFAnalysis, TimeframeBias
from atlas.domain.models.news import NewsFilterStatus
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.pipeline import PipelineStatus
from atlas.domain.models.price_action import PriceActionResult
from atlas.domain.models.smc import SMCAnalysisResult
from atlas.domain.models.strategy import StrategyProfile
from atlas.domain.models.technical import TechnicalAnalysisResult
from atlas.domain.models.validation import ValidationResult
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def _trigger_bar(instrument: Instrument) -> OHLCVBar:
    return OHLCVBar(
        instrument=instrument,
        timeframe=Timeframe.M15,
        open_time=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100"),
        volume=Decimal("100"),
    )


@pytest.fixture
def pipeline_orchestrator():
    instrument = _instrument()
    strategy = StrategyProfile(
        id="test",
        name="Test",
        min_confluence_score=Decimal("0.70"),
        enabled_directions=(Direction.BUY, Direction.SELL),
        confluence_weights={
            "mtf_alignment": Decimal("0.25"),
            "smc_structure": Decimal("0.25"),
            "price_action": Decimal("0.20"),
            "technical_levels": Decimal("0.15"),
            "market_context": Decimal("0.15"),
        },
        active_timeframes=(Timeframe.H4,),
        allowed_sessions=(),
        validation_rule_flags={},
        is_active=True,
        updated_at=datetime.now(UTC),
    )
    context = MarketContext(
        instrument=instrument,
        primary_session=MagicMock(value="london"),
        active_sessions=(),
        volatility_regime=MagicMock(value="normal"),
        spread_status=MagicMock(value="normal"),
        structural_bias=Bias.BULLISH,
        atr_value=Decimal("2.5"),
        atr_percentile=Decimal("45"),
        computed_at=datetime.now(UTC),
    )
    mtf = MTFAnalysis(
        instrument=instrument,
        biases=(TimeframeBias(Timeframe.H4, Bias.BULLISH, Decimal("0.8"), "x", ()),),
        alignment_score=Decimal("0.8"),
        dominant_bias=Bias.BULLISH,
        has_conflict=False,
        distant_conflict=False,
        aligned=True,
        computed_at=datetime.now(UTC),
    )
    technical = TechnicalAnalysisResult(
        instrument=instrument,
        timeframe=Timeframe.M15,
        trend=Trend.UPTREND,
        key_levels=(),
        nearest_support=Decimal("95"),
        nearest_resistance=Decimal("115"),
        indicator_context={},
        bullish_context_score=Decimal("0.5"),
        bearish_context_score=Decimal("0.1"),
        computed_at=datetime.now(UTC),
    )
    smc = SMCAnalysisResult(
        instrument=instrument,
        timeframe=Timeframe.M15,
        trend=Trend.UPTREND,
        last_bos=None,
        last_choch=None,
        order_blocks=(),
        liquidity_pools=(),
        fair_value_gaps=(),
        directional_bias=Bias.BULLISH,
        computed_at=datetime.now(UTC),
    )
    price_action = PriceActionResult(
        instrument=instrument,
        timeframe=Timeframe.M15,
        patterns=(),
        strongest_pattern=None,
        computed_at=datetime.now(UTC),
    )
    confluence = ConfluenceResult(
        instrument=instrument,
        suggested_direction=Direction.BUY,
        total_score=Decimal("0.80"),
        raw_score=Decimal("0.80"),
        bullish_raw=Decimal("0.80"),
        bearish_raw=Decimal("0.05"),
        news_penalty=Decimal("0"),
        module_scores=(),
        evidence=(),
        evidence_count=4,
        has_conflict=False,
        strategy_profile_id="test",
        computed_at=datetime.now(UTC),
    )
    validation = ValidationResult(
        instrument=instrument,
        direction=Direction.BUY,
        is_valid=True,
        rules=(),
        failed_rules=(),
        strategy_profile_id="test",
        validated_at=datetime.now(UTC),
    )
    news = NewsFilterStatus(
        is_blocked=False,
        is_soft_downgrade=False,
        confluence_penalty=Decimal("0"),
        next_event=None,
        as_of=datetime.now(UTC),
    )
    decision = TradingDecision(
        id=uuid4(),
        instrument=instrument,
        direction=Direction.BUY,
        is_actionable=True,
        confluence_score=Decimal("0.80"),
        strategy_id="test",
        reason="Confluence and validation passed",
        correlation_id="test-cid",
        decided_at=datetime.now(UTC),
    )

    market_data = MagicMock()
    market_data.get_recent_bars = AsyncMock(return_value=[_trigger_bar(instrument)])

    market_context = MagicMock()
    market_context.analyze_symbol = AsyncMock(return_value=context)
    mtf_service = MagicMock()
    mtf_service.analyze_symbol = AsyncMock(return_value=mtf)
    technical_service = MagicMock()
    technical_service.analyze_symbol = AsyncMock(return_value=technical)
    smc_service = MagicMock()
    smc_service.analyze_symbol = AsyncMock(return_value=smc)
    price_action_service = MagicMock()
    price_action_service.config = MagicMock(bar_lookback=120)
    price_action_service.analyze = MagicMock(return_value=price_action)
    news_filter = MagicMock()
    news_filter.check = MagicMock(return_value=news)
    confluence_service = MagicMock()
    confluence_service.calculate = MagicMock(return_value=confluence)
    validation_service = MagicMock()
    validation_service.validate = MagicMock(return_value=validation)
    strategy_engine = MagicMock()
    strategy_engine.get_active = AsyncMock(return_value=strategy)

    dedupe = MagicMock()
    dedupe.try_acquire = AsyncMock(return_value=True)

    bus = InMemoryEventBus()
    events: list[str] = []
    bus.subscribe("pipeline.completed", lambda e: events.append(e.event_type))

    decision_engine = DecisionEngineService(event_bus=bus)
    decision_engine.resolve = MagicMock(return_value=decision)
    decision_engine.emit = AsyncMock()

    orchestrator = AnalysisPipelineOrchestrator(
        market_data_service=market_data,
        market_context_service=market_context,
        mtf_service=mtf_service,
        technical_analysis_service=technical_service,
        smc_service=smc_service,
        price_action_service=price_action_service,
        news_filter=news_filter,
        confluence_service=confluence_service,
        trade_validation_service=validation_service,
        decision_engine=decision_engine,
        strategy_engine=strategy_engine,
        dedupe_cache=dedupe,
        event_bus=bus,
        config=PipelineConfig(risk_enabled=False),
    )
    return orchestrator, events, instrument


@pytest.mark.asyncio
async def test_pipeline_completes_all_stages(pipeline_orchestrator) -> None:
    orchestrator, events, instrument = pipeline_orchestrator
    run = await orchestrator.run(instrument, _trigger_bar(instrument), correlation_id="test-cid")

    assert run.status == PipelineStatus.COMPLETED
    assert run.correlation_id == "test-cid"
    assert "decision_engine" in run.stage_results
    assert run.stage_results["risk"].status == "skipped"
    assert events == ["pipeline.completed"]


@pytest.mark.asyncio
async def test_pipeline_dedupe_skips_second_run(pipeline_orchestrator) -> None:
    orchestrator, _, instrument = pipeline_orchestrator
    orchestrator.dedupe_cache.try_acquire = AsyncMock(side_effect=[True, False])

    first = await orchestrator.run(instrument, _trigger_bar(instrument))
    second = await orchestrator.run(instrument, _trigger_bar(instrument))

    assert first.status == PipelineStatus.COMPLETED
    assert second.status == PipelineStatus.SKIPPED


@pytest.mark.asyncio
async def test_non_critical_failure_continues(pipeline_orchestrator) -> None:
    orchestrator, events, instrument = pipeline_orchestrator
    orchestrator.technical_analysis_service.analyze_symbol = AsyncMock(return_value=None)

    run = await orchestrator.run(instrument, _trigger_bar(instrument))

    assert run.status == PipelineStatus.COMPLETED
    assert run.stage_results["technical_analysis"].status == "warning"
    assert events == ["pipeline.completed"]


@pytest.mark.asyncio
async def test_no_lookahead_uses_trigger_bar_time(pipeline_orchestrator) -> None:
    orchestrator, _, instrument = pipeline_orchestrator
    trigger = _trigger_bar(instrument)

    await orchestrator.run(instrument, trigger)

    orchestrator.market_context_service.analyze_symbol.assert_awaited_with(
        instrument.symbol,
        as_of=trigger.open_time,
        publish_event=False,
    )
    orchestrator.market_data_service.get_recent_bars.assert_awaited_with(
        instrument,
        Timeframe.M15,
        limit=orchestrator.price_action_service.config.bar_lookback,
        as_of=trigger.open_time,
    )


@pytest.mark.asyncio
async def test_critical_failure_emits_wait(pipeline_orchestrator) -> None:
    orchestrator, _, instrument = pipeline_orchestrator
    orchestrator.market_context_service.analyze_symbol = AsyncMock(
        side_effect=RuntimeError("context failed")
    )

    run = await orchestrator.run(instrument, _trigger_bar(instrument))

    assert run.status == PipelineStatus.FAILED
    assert run.decision_id is not None
    orchestrator.decision_engine.emit.assert_awaited()
