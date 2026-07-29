"""Confluence service tests."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from atlas.application.confluence.service import ConfluenceConfig, ConfluenceService
from atlas.domain.events.base import DomainEvent
from atlas.domain.models.enums import Bias, Direction, Timeframe, Trend
from atlas.domain.models.market_context import MarketContext
from atlas.domain.models.mtf import MTFAnalysis, TimeframeBias
from atlas.domain.models.news import NewsFilterStatus
from atlas.domain.models.price_action import PriceActionResult
from atlas.domain.models.smc import SMCAnalysisResult
from atlas.domain.models.strategy import StrategyProfile
from atlas.domain.models.technical import TechnicalAnalysisResult
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus


@pytest.fixture
def confluence_service():
    instrument = MagicMock(symbol="XAUUSD")
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
        biases=(
            TimeframeBias(
                timeframe=Timeframe.H4,
                bias=Bias.BULLISH,
                confidence=Decimal("0.8"),
                trend_source="swing_structure",
                key_levels=(),
            ),
        ),
        alignment_score=Decimal("0.80"),
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
        nearest_support=None,
        nearest_resistance=None,
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
    news_status = NewsFilterStatus(
        is_blocked=False,
        is_soft_downgrade=False,
        confluence_penalty=Decimal("0"),
        next_event=None,
        as_of=datetime.now(UTC),
    )

    market_context_service = MagicMock()
    market_context_service.analyze_symbol = AsyncMock(return_value=context)
    mtf_service = MagicMock()
    mtf_service.analyze_symbol = AsyncMock(return_value=mtf)
    technical_service = MagicMock()
    technical_service.analyze_symbol = AsyncMock(return_value=technical)
    smc_service = MagicMock()
    smc_service.analyze_symbol = AsyncMock(return_value=smc)
    price_action_service = MagicMock()
    price_action_service.analyze_symbol = AsyncMock(return_value=price_action)
    strategy_engine = MagicMock()
    strategy_engine.get_active = AsyncMock(return_value=strategy)
    news_filter = MagicMock()
    news_filter.check = MagicMock(return_value=news_status)

    bus = InMemoryEventBus()
    events: list[DomainEvent] = []
    bus.subscribe("confluence.calculated", lambda e: events.append(e))

    service = ConfluenceService(
        market_context_service=market_context_service,
        mtf_service=mtf_service,
        technical_analysis_service=technical_service,
        smc_service=smc_service,
        price_action_service=price_action_service,
        news_filter=news_filter,
        strategy_engine=strategy_engine,
        event_bus=bus,
        config=ConfluenceConfig(min_evidence_count=1),
    )
    return service, events


@pytest.mark.asyncio
async def test_calculate_symbol_publishes_event(confluence_service) -> None:
    service, events = confluence_service
    result = await service.calculate_symbol("XAUUSD")
    assert result is not None
    assert len(events) == 1
    assert events[0].event_type == "confluence.calculated"
