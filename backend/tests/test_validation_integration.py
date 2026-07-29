"""Confluence to validation integration test."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

from atlas.application.validation.service import TradeValidationService
from atlas.domain.models.enums import (
    Bias,
    Direction,
    SpreadStatus,
    Timeframe,
    TradingSession,
    Trend,
    VolatilityRegime,
)
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.market_context import MarketContext
from atlas.domain.models.mtf import MTFAnalysis, TimeframeBias
from atlas.domain.models.news import NewsFilterStatus
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.price_action import CandlePattern, PriceActionResult
from atlas.domain.models.smc import SMCAnalysisResult, StructureBreak
from atlas.domain.models.strategy import StrategyProfile
from atlas.domain.models.technical import TechnicalAnalysisResult
from atlas.domain.models.validation import ValidationContext
from atlas.domain.services.confluence_scoring import calculate_confluence
from atlas.domain.services.validation_rules import validate_context


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def test_confluence_to_validation_pipeline() -> None:
    instrument = _instrument()
    strategy = StrategyProfile(
        id="test",
        name="Test",
        min_confluence_score=Decimal("0.70"),
        enabled_directions=(Direction.BUY,),
        confluence_weights={
            "mtf_alignment": Decimal("0.25"),
            "smc_structure": Decimal("0.25"),
            "price_action": Decimal("0.20"),
            "technical_levels": Decimal("0.15"),
            "market_context": Decimal("0.15"),
        },
        active_timeframes=(Timeframe.H4,),
        allowed_sessions=(TradingSession.LONDON,),
        validation_rule_flags={
            "mtf_alignment_minimum": True,
            "confluence_score_minimum": True,
            "no_counter_trend": True,
            "minimum_rr_potential": True,
            "news_block": True,
            "session_check": True,
            "spread_check": True,
            "volatility_check": True,
        },
        is_active=True,
        updated_at=datetime.now(UTC),
    )
    mtf = MTFAnalysis(
        instrument=instrument,
        biases=(
            TimeframeBias(Timeframe.D1, Bias.BULLISH, Decimal("0.8"), "x", ()),
            TimeframeBias(Timeframe.H4, Bias.BULLISH, Decimal("0.8"), "x", ()),
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
        last_bos=StructureBreak("bos", Bias.BULLISH, 10, Decimal("2350")),
        last_choch=None,
        order_blocks=(),
        liquidity_pools=(),
        fair_value_gaps=(),
        directional_bias=Bias.BULLISH,
        computed_at=datetime.now(UTC),
    )
    pattern = CandlePattern("engulfing", Bias.BULLISH, 1, Decimal("0.8"), False)
    price_action = PriceActionResult(
        instrument=instrument,
        timeframe=Timeframe.M15,
        patterns=(pattern,),
        strongest_pattern=pattern,
        computed_at=datetime.now(UTC),
    )
    context = MarketContext(
        instrument=instrument,
        primary_session=TradingSession.LONDON,
        active_sessions=(TradingSession.LONDON,),
        volatility_regime=VolatilityRegime.NORMAL,
        spread_status=SpreadStatus.NORMAL,
        structural_bias=Bias.BULLISH,
        atr_value=Decimal("2.5"),
        atr_percentile=Decimal("45"),
        computed_at=datetime.now(UTC),
    )
    news = NewsFilterStatus(
        is_blocked=False,
        is_soft_downgrade=False,
        confluence_penalty=Decimal("0"),
        next_event=None,
        as_of=datetime.now(UTC),
    )
    confluence = calculate_confluence(
        instrument,
        mtf,
        technical,
        smc,
        price_action,
        context,
        news,
        strategy,
        computed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert confluence.suggested_direction == Direction.BUY

    trigger_bar = OHLCVBar(
        instrument=instrument,
        timeframe=Timeframe.M15,
        open_time=datetime(2026, 1, 1, tzinfo=UTC),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100"),
        volume=Decimal("100"),
    )
    validation_context = ValidationContext(
        confluence=confluence,
        mtf=mtf,
        context=context,
        technical=technical,
        smc=smc,
        news=news,
        strategy=strategy,
        trigger_bar=trigger_bar,
    )
    is_valid, _ = validate_context(validation_context)
    assert is_valid is True

    service = TradeValidationService(
        market_data_service=MagicMock(),
        confluence_service=MagicMock(),
        mtf_service=MagicMock(),
        technical_analysis_service=MagicMock(),
        smc_service=MagicMock(),
        market_context_service=MagicMock(),
        news_filter=MagicMock(),
        strategy_engine=MagicMock(),
        event_bus=MagicMock(),
    )
    result = service.validate(validation_context)
    assert result.is_valid is True
    assert result.direction == Direction.BUY
