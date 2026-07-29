"""Structural bias from higher-timeframe swing structure (Spec 03)."""

from atlas.domain.models.enums import Bias
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.services.swing_detection import find_swing_highs, find_swing_lows


def compute_structural_bias(bars: list[OHLCVBar], swing_lookback: int = 2) -> Bias:
    """Classify H4 structure from last two swing highs and lows."""
    highs = find_swing_highs(bars, lookback=swing_lookback)
    lows = find_swing_lows(bars, lookback=swing_lookback)

    if len(highs) < 2 or len(lows) < 2:
        return Bias.NEUTRAL

    _, prev_high = highs[-2]
    _, last_high = highs[-1]
    _, prev_low = lows[-2]
    _, last_low = lows[-1]

    higher_highs = last_high > prev_high
    higher_lows = last_low > prev_low
    lower_highs = last_high < prev_high
    lower_lows = last_low < prev_low

    if higher_highs and higher_lows:
        return Bias.BULLISH
    if lower_highs and lower_lows:
        return Bias.BEARISH
    return Bias.NEUTRAL
