"""Structural bias and swing detection tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from atlas.domain.models.enums import Bias, Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.services.structural_bias import compute_structural_bias
from atlas.domain.services.swing_detection import find_swing_highs, find_swing_lows


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def _bar(instrument: Instrument, i: int, high: Decimal, low: Decimal) -> OHLCVBar:
    return OHLCVBar(
        instrument=instrument,
        timeframe=Timeframe.H4,
        open_time=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=4 * i),
        open=(high + low) / 2,
        high=high,
        low=low,
        close=(high + low) / 2,
        volume=Decimal("100"),
    )


def test_swing_detection_excludes_last_two_bars() -> None:
    instrument = _instrument()
    highs = [Decimal(v) for v in [10, 12, 15, 13, 11, 14, 16, 12, 10, 9]]
    bars = [_bar(instrument, i, Decimal(h), Decimal(h) - 2) for i, h in enumerate(highs)]
    swings = find_swing_highs(bars)
    assert all(index < len(bars) - 2 for index, _ in swings)


def test_structural_bias_bullish_on_hh_hl() -> None:
    instrument = _instrument()
    highs = [10, 11, 15, 12, 11, 13, 18, 14, 13, 16, 22, 17, 16, 20, 26]
    lows = [5, 6, 7, 6, 5, 7, 9, 8, 7, 9, 11, 10, 9, 12, 14]
    bars = [
        _bar(instrument, i, Decimal(highs[i]), Decimal(lows[i]))
        for i in range(len(highs))
    ]
    assert compute_structural_bias(bars) == Bias.BULLISH


def test_structural_bias_neutral_with_insufficient_swings() -> None:
    instrument = _instrument()
    bars = [_bar(instrument, i, Decimal("10"), Decimal("8")) for i in range(5)]
    assert compute_structural_bias(bars) == Bias.NEUTRAL


def test_swing_lows_detected() -> None:
    instrument = _instrument()
    lows = [20, 19, 18, 17, 16, 15, 14, 12, 14, 16]
    bars = [_bar(instrument, i, Decimal(low + 2), Decimal(low)) for i, low in enumerate(lows)]
    swings = find_swing_lows(bars)
    assert len(swings) >= 1
