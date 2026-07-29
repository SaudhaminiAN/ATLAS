"""Trend classification from swing structure (Spec 05)."""

from atlas.domain.models.enums import Trend
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.services.swing_detection import find_swing_highs, find_swing_lows


def classify_trend(bars: list[OHLCVBar], swing_lookback: int = 2) -> Trend:
    """Classify trend as uptrend, downtrend, or ranging."""
    highs = find_swing_highs(bars, lookback=swing_lookback)
    lows = find_swing_lows(bars, lookback=swing_lookback)

    if len(highs) < 2 or len(lows) < 2:
        return Trend.RANGING

    _, prev_high = highs[-2]
    _, last_high = highs[-1]
    _, prev_low = lows[-2]
    _, last_low = lows[-1]

    if last_high > prev_high and last_low > prev_low:
        return Trend.UPTREND
    if last_high < prev_high and last_low < prev_low:
        return Trend.DOWNTREND
    return Trend.RANGING
