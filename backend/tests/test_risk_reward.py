"""Minimum R:R golden tests."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from atlas.domain.models.enums import Bias, Direction, Timeframe, Trend
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.smc import OrderBlock, SMCAnalysisResult
from atlas.domain.models.technical import TechnicalAnalysisResult
from atlas.domain.services.risk_reward import evaluate_minimum_rr


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def _bar(close: Decimal) -> OHLCVBar:
    instrument = _instrument()
    return OHLCVBar(
        instrument=instrument,
        timeframe=Timeframe.M15,
        open_time=datetime(2026, 1, 1, tzinfo=UTC),
        open=close,
        high=close + Decimal("1"),
        low=close - Decimal("1"),
        close=close,
        volume=Decimal("100"),
    )


def _technical(
    *,
    support: Decimal | None,
    resistance: Decimal | None,
) -> TechnicalAnalysisResult:
    return TechnicalAnalysisResult(
        instrument=_instrument(),
        timeframe=Timeframe.M15,
        trend=Trend.UPTREND,
        key_levels=(),
        nearest_support=support,
        nearest_resistance=resistance,
        indicator_context={},
        bullish_context_score=Decimal("0.5"),
        bearish_context_score=Decimal("0.1"),
        computed_at=datetime.now(UTC),
    )


def _smc() -> SMCAnalysisResult:
    return SMCAnalysisResult(
        instrument=_instrument(),
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


def test_buy_rr_passes_with_structural_levels() -> None:
    passed, reason = evaluate_minimum_rr(
        Direction.BUY,
        _bar(Decimal("100")),
        _technical(support=Decimal("95"), resistance=Decimal("115")),
        _smc(),
    )
    assert passed is True
    assert "meets minimum" in reason


def test_buy_rr_fails_when_reward_too_small() -> None:
    passed, reason = evaluate_minimum_rr(
        Direction.BUY,
        _bar(Decimal("100")),
        _technical(support=Decimal("95"), resistance=Decimal("104")),
        _smc(),
    )
    assert passed is False
    assert "below minimum" in reason


def test_buy_rr_fails_without_levels() -> None:
    passed, reason = evaluate_minimum_rr(
        Direction.BUY,
        _bar(Decimal("100")),
        _technical(support=None, resistance=None),
        _smc(),
    )
    assert passed is False
    assert reason == "No structural SL/TP levels"


def test_buy_rr_uses_order_block_stop_fallback() -> None:
    smc = SMCAnalysisResult(
        instrument=_instrument(),
        timeframe=Timeframe.M15,
        trend=Trend.UPTREND,
        last_bos=None,
        last_choch=None,
        order_blocks=(
            OrderBlock(
                direction=Bias.BULLISH,
                bar_index=1,
                zone_low=Decimal("96"),
                zone_high=Decimal("98"),
                is_mitigated=False,
            ),
        ),
        liquidity_pools=(),
        fair_value_gaps=(),
        directional_bias=Bias.BULLISH,
        computed_at=datetime.now(UTC),
    )
    passed, _ = evaluate_minimum_rr(
        Direction.BUY,
        _bar(Decimal("100")),
        _technical(support=None, resistance=Decimal("115")),
        smc,
    )
    assert passed is True
