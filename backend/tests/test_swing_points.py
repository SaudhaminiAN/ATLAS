"""Swing point shared utility tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from atlas.domain.models.enums import Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.services.swing_detection import find_swing_highs
from atlas.domain.services.swing_points import detect_swings


def _bar(i: int, high: Decimal, low: Decimal) -> OHLCVBar:
    instrument = Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )
    return OHLCVBar(
        instrument=instrument,
        timeframe=Timeframe.M15,
        open_time=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=15 * i),
        open=(high + low) / 2,
        high=high,
        low=low,
        close=(high + low) / 2,
        volume=Decimal("100"),
    )


def test_detect_swings_matches_swing_detection() -> None:
    highs = [Decimal(v) for v in [10, 12, 15, 13, 11, 14, 16, 12, 10, 9]]
    bars = [_bar(i, h, h - Decimal(2)) for i, h in enumerate(highs)]
    swings = detect_swings(bars)
    swing_highs = find_swing_highs(bars)
    assert len([s for s in swings if s.swing_type == "high"]) == len(swing_highs)


def test_zero_range_bar_skipped() -> None:
    bars = [_bar(0, Decimal("10"), Decimal("10"))]
    assert detect_swings(bars) == []
