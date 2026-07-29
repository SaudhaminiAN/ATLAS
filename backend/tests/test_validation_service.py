"""Trade validation service tests."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from atlas.application.validation.service import TradeValidationConfig, TradeValidationService
from atlas.domain.events.base import DomainEvent
from atlas.domain.models.confluence import ConfluenceResult
from atlas.domain.models.enums import Bias, Direction, Timeframe, Trend
from atlas.domain.models.market_context import MarketContext
from atlas.domain.models.mtf import MTFAnalysis, TimeframeBias
from atlas.domain.models.news import NewsFilterStatus
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.smc import SMCAnalysisResult
from atlas.domain.models.strategy import StrategyProfile
from atlas.domain.models.technical import TechnicalAnalysisResult
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus


@pytest.fixture
def validation_service():
    instrument = MagicMock(symbol="XAUUSD")
    strategy = StrategyProfile(
        id="test",
        name="Test",
        min_confluence_score=Decimal("0.70"),
        enabled_directions=(Direction.BUY,),
        confluence_weights={},
        active_timeframes=(Timeframe.H4,),
        allowed_sessions=(),
        validation_rule_flags={"news_block": True, "mtf_alignment_minimum": False},
        is_active=True,
        updated_at=datetime.now(UTC),
    )
    bar = OHLCVBar(
        instrument=instrument,
        timeframe=Timeframe.M15,
        open_time=datetime(2026, 1, 1, tzinfo=UTC),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100"),
        volume=Decimal("100"),
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
    mtf = MTFAnalysis(
        instrument=instrument,
        biases=(
            TimeframeBias(Timeframe.H4, Bias.BULLISH, Decimal("0.8"), "x", ()),
        ),
        alignment_score=Decimal("0.8"),
        dominant_bias=Bias.BULLISH,
        has_conflict=False,
        distant_conflict=False,
        aligned=True,
        computed_at=datetime.now(UTC),
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

    market_data = MagicMock()
    market_data.get_instrument = AsyncMock(return_value=instrument)
    market_data.get_recent_bars = AsyncMock(return_value=[bar])
    confluence_service = MagicMock()
    confluence_service.calculate_symbol = AsyncMock(return_value=confluence)
    mtf_service = MagicMock()
    mtf_service.analyze_symbol = AsyncMock(return_value=mtf)
    market_context_service = MagicMock()
    market_context_service.analyze_symbol = AsyncMock(return_value=context)
    technical_service = MagicMock()
    technical_service.analyze_symbol = AsyncMock(return_value=technical)
    smc_service = MagicMock()
    smc_service.analyze_symbol = AsyncMock(return_value=smc)
    strategy_engine = MagicMock()
    strategy_engine.get_active = AsyncMock(return_value=strategy)
    news_filter = MagicMock()
    news_filter.check = MagicMock(
        return_value=NewsFilterStatus(
            is_blocked=False,
            is_soft_downgrade=False,
            confluence_penalty=Decimal("0"),
            next_event=None,
            as_of=datetime.now(UTC),
        )
    )

    bus = InMemoryEventBus()
    events: list[DomainEvent] = []
    bus.subscribe("validation.completed", lambda e: events.append(e))

    service = TradeValidationService(
        market_data_service=market_data,
        confluence_service=confluence_service,
        mtf_service=mtf_service,
        technical_analysis_service=technical_service,
        smc_service=smc_service,
        market_context_service=market_context_service,
        news_filter=news_filter,
        strategy_engine=strategy_engine,
        event_bus=bus,
        config=TradeValidationConfig(),
    )
    return service, events


@pytest.mark.asyncio
async def test_validate_symbol_publishes_event(validation_service) -> None:
    service, events = validation_service
    result = await service.validate_symbol("XAUUSD")
    assert result is not None
    assert len(events) == 1
    assert events[0].event_type == "validation.completed"
