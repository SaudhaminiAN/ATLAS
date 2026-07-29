"""Validation rules tests."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from atlas.domain.models.confluence import ConfluenceResult
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
from atlas.domain.models.smc import SMCAnalysisResult
from atlas.domain.models.strategy import StrategyProfile
from atlas.domain.models.technical import TechnicalAnalysisResult
from atlas.domain.models.validation import ValidationContext
from atlas.domain.services.validation_rules import (
    RULE_NAMES,
    evaluate_validation_rules,
    validate_context,
)


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def _strategy(**rule_flags) -> StrategyProfile:
    flags = {name: True for name in RULE_NAMES}
    flags.update(rule_flags)
    return StrategyProfile(
        id="test",
        name="Test",
        min_confluence_score=Decimal("0.70"),
        enabled_directions=(Direction.BUY, Direction.SELL),
        confluence_weights={},
        active_timeframes=(Timeframe.D1, Timeframe.H4),
        allowed_sessions=(TradingSession.LONDON, TradingSession.OVERLAP),
        validation_rule_flags=flags,
        is_active=True,
        updated_at=datetime.now(UTC),
    )


def _context(**overrides) -> ValidationContext:
    instrument = _instrument()
    base = ValidationContext(
        confluence=ConfluenceResult(
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
        ),
        mtf=MTFAnalysis(
            instrument=instrument,
            biases=(
                TimeframeBias(
                    Timeframe.D1,
                    Bias.BULLISH,
                    Decimal("0.8"),
                    "swing_structure",
                    (),
                ),
                TimeframeBias(
                    Timeframe.H4,
                    Bias.BULLISH,
                    Decimal("0.8"),
                    "swing_structure",
                    (),
                ),
            ),
            alignment_score=Decimal("0.80"),
            dominant_bias=Bias.BULLISH,
            has_conflict=False,
            distant_conflict=False,
            aligned=True,
            computed_at=datetime.now(UTC),
        ),
        context=MarketContext(
            instrument=instrument,
            primary_session=TradingSession.LONDON,
            active_sessions=(TradingSession.LONDON,),
            volatility_regime=VolatilityRegime.NORMAL,
            spread_status=SpreadStatus.NORMAL,
            structural_bias=Bias.BULLISH,
            atr_value=Decimal("2.5"),
            atr_percentile=Decimal("45"),
            computed_at=datetime.now(UTC),
        ),
        technical=TechnicalAnalysisResult(
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
        ),
        smc=SMCAnalysisResult(
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
        ),
        news=NewsFilterStatus(
            is_blocked=False,
            is_soft_downgrade=False,
            confluence_penalty=Decimal("0"),
            next_event=None,
            as_of=datetime.now(UTC),
        ),
        strategy=_strategy(),
        trigger_bar=OHLCVBar(
            instrument=instrument,
            timeframe=Timeframe.M15,
            open_time=datetime(2026, 1, 1, tzinfo=UTC),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=Decimal("100"),
        ),
    )
    return overrides.get("replace", base) if "replace" in overrides else base


def test_all_enabled_rules_pass() -> None:
    is_valid, rules = validate_context(_context())
    assert is_valid is True
    enabled_rules = [rule for rule in rules if rule.enabled]
    assert all(rule.passed for rule in enabled_rules)


def test_wait_direction_skips_rule_evaluation() -> None:
    ctx = _context()
    ctx = ValidationContext(
        confluence=ConfluenceResult(
            instrument=ctx.confluence.instrument,
            suggested_direction=Direction.WAIT,
            total_score=Decimal("0"),
            raw_score=Decimal("0"),
            bullish_raw=Decimal("0"),
            bearish_raw=Decimal("0"),
            news_penalty=Decimal("0"),
            module_scores=(),
            evidence=(),
            evidence_count=0,
            has_conflict=False,
            strategy_profile_id="test",
            computed_at=datetime.now(UTC),
        ),
        mtf=ctx.mtf,
        context=ctx.context,
        technical=ctx.technical,
        smc=ctx.smc,
        news=ctx.news,
        strategy=ctx.strategy,
        trigger_bar=ctx.trigger_bar,
    )
    is_valid, rules = validate_context(ctx)
    assert is_valid is False
    assert rules[0].reason == "No direction to validate"


def test_disabled_rule_is_skipped() -> None:
    ctx = _context()
    ctx = ValidationContext(
        confluence=ctx.confluence,
        mtf=MTFAnalysis(
            instrument=ctx.mtf.instrument,
            biases=ctx.mtf.biases,
            alignment_score=ctx.mtf.alignment_score,
            dominant_bias=ctx.mtf.dominant_bias,
            has_conflict=ctx.mtf.has_conflict,
            distant_conflict=ctx.mtf.distant_conflict,
            aligned=False,
            computed_at=ctx.mtf.computed_at,
        ),
        context=ctx.context,
        technical=ctx.technical,
        smc=ctx.smc,
        news=ctx.news,
        strategy=_strategy(mtf_alignment_minimum=False),
        trigger_bar=ctx.trigger_bar,
    )
    results = evaluate_validation_rules(ctx)
    mtf_rule = next(rule for rule in results if rule.rule_name == "mtf_alignment_minimum")
    assert mtf_rule.enabled is False
    assert mtf_rule.passed is True


def test_news_block_fails_when_blocked() -> None:
    ctx = _context()
    ctx = ValidationContext(
        confluence=ctx.confluence,
        mtf=ctx.mtf,
        context=ctx.context,
        technical=ctx.technical,
        smc=ctx.smc,
        news=NewsFilterStatus(
            is_blocked=True,
            is_soft_downgrade=False,
            confluence_penalty=Decimal("0"),
            next_event=None,
            as_of=datetime.now(UTC),
        ),
        strategy=ctx.strategy,
        trigger_bar=ctx.trigger_bar,
    )
    is_valid, rules = validate_context(ctx)
    assert is_valid is False
    assert "news_block" in [rule.rule_name for rule in rules if not rule.passed]


def test_counter_trend_fails_for_buy_against_bearish_h4() -> None:
    ctx = _context()
    ctx = ValidationContext(
        confluence=ctx.confluence,
        mtf=MTFAnalysis(
            instrument=ctx.mtf.instrument,
            biases=(
                TimeframeBias(Timeframe.D1, Bias.BULLISH, Decimal("0.8"), "x", ()),
                TimeframeBias(Timeframe.H4, Bias.BEARISH, Decimal("0.8"), "x", ()),
            ),
            alignment_score=ctx.mtf.alignment_score,
            dominant_bias=ctx.mtf.dominant_bias,
            has_conflict=ctx.mtf.has_conflict,
            distant_conflict=ctx.mtf.distant_conflict,
            aligned=ctx.mtf.aligned,
            computed_at=ctx.mtf.computed_at,
        ),
        context=ctx.context,
        technical=ctx.technical,
        smc=ctx.smc,
        news=ctx.news,
        strategy=ctx.strategy,
        trigger_bar=ctx.trigger_bar,
    )
    is_valid, _ = validate_context(ctx)
    assert is_valid is False


def test_volatility_extreme_fails() -> None:
    ctx = _context()
    ctx = ValidationContext(
        confluence=ctx.confluence,
        mtf=ctx.mtf,
        context=MarketContext(
            instrument=ctx.context.instrument,
            primary_session=ctx.context.primary_session,
            active_sessions=ctx.context.active_sessions,
            volatility_regime=VolatilityRegime.EXTREME,
            spread_status=ctx.context.spread_status,
            structural_bias=ctx.context.structural_bias,
            atr_value=ctx.context.atr_value,
            atr_percentile=Decimal("96"),
            computed_at=ctx.context.computed_at,
        ),
        technical=ctx.technical,
        smc=ctx.smc,
        news=ctx.news,
        strategy=ctx.strategy,
        trigger_bar=ctx.trigger_bar,
    )
    is_valid, _ = validate_context(ctx)
    assert is_valid is False
