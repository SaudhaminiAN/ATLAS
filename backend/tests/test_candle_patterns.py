"""Candle pattern golden tests (Spec 07)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from atlas.domain.models.enums import Bias, Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.services.candle_patterns import (
    detect_engulfing,
    detect_inside_bar,
    detect_patterns_on_closed_bar,
    detect_pin_bar,
)


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def _bar(
    i: int,
    *,
    open_: Decimal,
    high: Decimal,
    low: Decimal,
    close: Decimal,
    instrument: Instrument | None = None,
) -> OHLCVBar:
    instrument = instrument or _instrument()
    return OHLCVBar(
        instrument=instrument,
        timeframe=Timeframe.M15,
        open_time=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=15 * i),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=Decimal("100"),
    )


def test_bullish_pin_bar_detected() -> None:
    bar = _bar(
        0,
        open_=Decimal("102"),
        high=Decimal("103"),
        low=Decimal("95"),
        close=Decimal("101"),
    )
    pattern = detect_pin_bar(bar, 0)
    assert pattern is not None
    assert pattern.pattern_type == "pin_bar"
    assert pattern.direction == Bias.BULLISH


def test_bullish_pin_bar_near_miss() -> None:
    bar = _bar(
        0,
        open_=Decimal("102"),
        high=Decimal("103"),
        low=Decimal("98"),
        close=Decimal("101"),
    )
    assert detect_pin_bar(bar, 0) is None


def test_doji_skips_pin_bar() -> None:
    bar = _bar(
        0,
        open_=Decimal("100"),
        high=Decimal("100"),
        low=Decimal("100"),
        close=Decimal("100"),
    )
    assert detect_pin_bar(bar, 0) is None


def test_bullish_engulfing_detected() -> None:
    prev = _bar(
        0,
        open_=Decimal("105"),
        high=Decimal("106"),
        low=Decimal("99"),
        close=Decimal("100"),
    )
    curr = _bar(
        1,
        open_=Decimal("99"),
        high=Decimal("108"),
        low=Decimal("98"),
        close=Decimal("107"),
    )
    pattern = detect_engulfing(prev, curr, 1)
    assert pattern is not None
    assert pattern.pattern_type == "engulfing"
    assert pattern.direction == Bias.BULLISH


def test_engulfing_near_miss() -> None:
    prev = _bar(
        0,
        open_=Decimal("105"),
        high=Decimal("106"),
        low=Decimal("99"),
        close=Decimal("100"),
    )
    curr = _bar(
        1,
        open_=Decimal("101"),
        high=Decimal("104"),
        low=Decimal("100"),
        close=Decimal("103"),
    )
    assert detect_engulfing(prev, curr, 1) is None


def test_inside_bar_detected() -> None:
    prev = _bar(
        0,
        open_=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
    )
    curr = _bar(
        1,
        open_=Decimal("102"),
        high=Decimal("108"),
        low=Decimal("95"),
        close=Decimal("106"),
    )
    pattern = detect_inside_bar(prev, curr, 1)
    assert pattern is not None
    assert pattern.pattern_type == "inside_bar"


def test_inside_bar_near_miss() -> None:
    prev = _bar(
        0,
        open_=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
    )
    curr = _bar(
        1,
        open_=Decimal("95"),
        high=Decimal("112"),
        low=Decimal("94"),
        close=Decimal("111"),
    )
    assert detect_inside_bar(prev, curr, 1) is None


def test_multiple_patterns_on_same_bar() -> None:
    bars = [
        _bar(
            0,
            open_=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
        ),
        _bar(
            1,
            open_=Decimal("105"),
            high=Decimal("106"),
            low=Decimal("99"),
            close=Decimal("100"),
        ),
        _bar(
            2,
            open_=Decimal("99"),
            high=Decimal("108"),
            low=Decimal("95"),
            close=Decimal("107"),
        ),
    ]
    patterns = detect_patterns_on_closed_bar(bars)
    pattern_types = {pattern.pattern_type for pattern in patterns}
    assert "engulfing" in pattern_types
