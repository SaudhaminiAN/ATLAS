"""Swing point detection service (shared Spec 05/06)."""

from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.swing import SwingPoint
from atlas.domain.services.swing_detection import find_swing_highs, find_swing_lows


def _bar_has_range(bar: OHLCVBar) -> bool:
    return bar.high > bar.low


def detect_swings(bars: list[OHLCVBar], lookback: int = 2) -> list[SwingPoint]:
    """Detect swing highs and lows; skip zero-range bars."""
    swings: list[SwingPoint] = []
    for index, price in find_swing_highs(bars, lookback):
        if _bar_has_range(bars[index]):
            swings.append(SwingPoint(bar_index=index, price=price, swing_type="high"))
    for index, price in find_swing_lows(bars, lookback):
        if _bar_has_range(bars[index]):
            swings.append(SwingPoint(bar_index=index, price=price, swing_type="low"))
    swings.sort(key=lambda point: point.bar_index)
    return swings
