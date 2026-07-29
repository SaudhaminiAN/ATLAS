"""Confluence scoring golden tests."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

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
from atlas.domain.models.price_action import CandlePattern, PriceActionResult
from atlas.domain.models.smc import SMCAnalysisResult, StructureBreak
from atlas.domain.models.strategy import StrategyProfile
from atlas.domain.models.technical import TechnicalAnalysisResult
from atlas.domain.services.confluence_scoring import (
    calculate_confluence,
    score_market_context,
    score_mtf,
    score_price_action,
    score_smc,
    score_technical,
)


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def _strategy() -> StrategyProfile:
    return StrategyProfile(
        id="xauusd_conservative",
        name="XAUUSD Conservative",
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
        allowed_sessions=(TradingSession.LONDON,),
        validation_rule_flags={},
        is_active=True,
        updated_at=datetime.now(UTC),
    )


def _news(penalty: Decimal = Decimal("0")) -> NewsFilterStatus:
    return NewsFilterStatus(
        is_blocked=False,
        is_soft_downgrade=penalty > 0,
        confluence_penalty=penalty,
        next_event=None,
        as_of=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _mtf(*, aligned: bool = True, bias: Bias = Bias.BULLISH) -> MTFAnalysis:
    return MTFAnalysis(
        instrument=_instrument(),
        biases=(
            TimeframeBias(
                timeframe=Timeframe.H4,
                bias=bias,
                confidence=Decimal("0.8"),
                trend_source="swing_structure",
                key_levels=(),
            ),
        ),
        alignment_score=Decimal("0.80"),
        dominant_bias=bias,
        has_conflict=False,
        distant_conflict=False,
        aligned=aligned,
        computed_at=datetime.now(UTC),
    )


def _technical(
    *,
    bullish: Decimal = Decimal("0.5"),
    bearish: Decimal = Decimal("0.1"),
) -> TechnicalAnalysisResult:
    return TechnicalAnalysisResult(
        instrument=_instrument(),
        timeframe=Timeframe.M15,
        trend=Trend.UPTREND,
        key_levels=(),
        nearest_support=None,
        nearest_resistance=None,
        indicator_context={},
        bullish_context_score=bullish,
        bearish_context_score=bearish,
        computed_at=datetime.now(UTC),
    )


def _smc(*, bias: Bias = Bias.BULLISH, with_bos: bool = True) -> SMCAnalysisResult:
    return SMCAnalysisResult(
        instrument=_instrument(),
        timeframe=Timeframe.M15,
        trend=Trend.UPTREND,
        last_bos=(
            StructureBreak("bos", Bias.BULLISH, 10, Decimal("2350")) if with_bos else None
        ),
        last_choch=None,
        order_blocks=(),
        liquidity_pools=(),
        fair_value_gaps=(),
        directional_bias=bias,
        computed_at=datetime.now(UTC),
    )


def _price_action(*, strength: Decimal = Decimal("0.8")) -> PriceActionResult:
    pattern = CandlePattern(
        pattern_type="engulfing",
        direction=Bias.BULLISH,
        bar_index=10,
        strength=strength,
        at_key_level=False,
    )
    return PriceActionResult(
        instrument=_instrument(),
        timeframe=Timeframe.M15,
        patterns=(pattern,),
        strongest_pattern=pattern,
        computed_at=datetime.now(UTC),
    )


def _context(*, bias: Bias = Bias.BULLISH) -> MarketContext:
    instrument = _instrument()
    return MarketContext(
        instrument=instrument,
        primary_session=TradingSession.LONDON,
        active_sessions=(TradingSession.LONDON,),
        volatility_regime=VolatilityRegime.NORMAL,
        spread_status=SpreadStatus.NORMAL,
        structural_bias=bias,
        atr_value=Decimal("2.5"),
        atr_percentile=Decimal("45"),
        computed_at=datetime.now(UTC),
    )


def test_score_mtf_requires_alignment() -> None:
    aligned = score_mtf(_mtf(aligned=True))
    unaligned = score_mtf(_mtf(aligned=False))
    assert aligned.score == Decimal("0.80")
    assert unaligned.score == Decimal("0")


def test_score_smc_uses_bos_strength() -> None:
    assert score_smc(_smc(with_bos=True)).score == Decimal("1.0")
    assert score_smc(_smc(with_bos=False)).score == Decimal("0.5")


def test_score_price_action_boosts_at_key_level() -> None:
    result = PriceActionResult(
        instrument=_instrument(),
        timeframe=Timeframe.M15,
        patterns=(),
        strongest_pattern=CandlePattern(
            "pin_bar",
            Bias.BULLISH,
            1,
            Decimal("0.80"),
            True,
        ),
        computed_at=datetime.now(UTC),
    )
    assert score_price_action(result).score == Decimal("0.88")


def test_score_technical_picks_dominant_side() -> None:
    bullish = score_technical(_technical(bullish=Decimal("0.5"), bearish=Decimal("0.2")))
    assert bullish.direction == Bias.BULLISH
    assert bullish.score == Decimal("0.5")


def test_market_context_extreme_volatility_zeroes_score() -> None:
    context = MarketContext(
        instrument=_instrument(),
        primary_session=TradingSession.LONDON,
        active_sessions=(TradingSession.LONDON,),
        volatility_regime=VolatilityRegime.EXTREME,
        spread_status=SpreadStatus.NORMAL,
        structural_bias=Bias.BULLISH,
        atr_value=Decimal("2.5"),
        atr_percentile=Decimal("95"),
        computed_at=datetime.now(UTC),
    )
    assert score_market_context(context).score == Decimal("0")


def test_bullish_modules_suggest_buy() -> None:
    result = calculate_confluence(
        _instrument(),
        _mtf(),
        _technical(),
        _smc(),
        _price_action(),
        _context(),
        _news(),
        _strategy(),
        computed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert result.suggested_direction == Direction.BUY
    assert result.total_score >= Decimal("0.70")
    assert result.evidence_count >= 3
    assert result.has_conflict is False


def test_news_penalty_can_force_wait() -> None:
    result = calculate_confluence(
        _instrument(),
        _mtf(),
        _technical(),
        _smc(),
        _price_action(strength=Decimal("0.6")),
        _context(),
        _news(penalty=Decimal("0.25")),
        _strategy(),
        computed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert result.suggested_direction == Direction.WAIT
    assert result.news_penalty == Decimal("0.25")


def test_conflicting_evidence_forces_wait() -> None:
    result = calculate_confluence(
        _instrument(),
        _mtf(bias=Bias.BULLISH),
        _technical(bullish=Decimal("0.1"), bearish=Decimal("0.6")),
        _smc(bias=Bias.BULLISH, with_bos=True),
        _price_action(),
        _context(bias=Bias.BULLISH),
        _news(),
        _strategy(),
        computed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert result.has_conflict is True
    assert result.suggested_direction == Direction.WAIT


def test_all_neutral_suggests_wait() -> None:
    result = calculate_confluence(
        _instrument(),
        _mtf(aligned=False, bias=Bias.NEUTRAL),
        _technical(bullish=Decimal("0.1"), bearish=Decimal("0.1")),
        _smc(bias=Bias.NEUTRAL, with_bos=False),
        PriceActionResult(
            instrument=_instrument(),
            timeframe=Timeframe.M15,
            patterns=(),
            strongest_pattern=None,
            computed_at=datetime.now(UTC),
        ),
        _context(bias=Bias.NEUTRAL),
        _news(),
        _strategy(),
        computed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert result.suggested_direction == Direction.WAIT
    assert result.total_score == Decimal("0")
    assert result.evidence_count == 0


def test_insufficient_evidence_forces_wait() -> None:
    strategy = StrategyProfile(
        id="test",
        name="Test",
        min_confluence_score=Decimal("0.50"),
        enabled_directions=(Direction.BUY,),
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
    result = calculate_confluence(
        _instrument(),
        _mtf(),
        _technical(bullish=Decimal("0.1"), bearish=Decimal("0.1")),
        _smc(bias=Bias.NEUTRAL, with_bos=False),
        PriceActionResult(
            instrument=_instrument(),
            timeframe=Timeframe.M15,
            patterns=(),
            strongest_pattern=None,
            computed_at=datetime.now(UTC),
        ),
        _context(bias=Bias.NEUTRAL),
        _news(),
        strategy,
        min_evidence_count=3,
        computed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert result.evidence_count < 3
    assert result.suggested_direction == Direction.WAIT
