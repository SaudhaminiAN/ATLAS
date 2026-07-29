"""BOS and CHoCH detection (Spec 06)."""

from atlas.domain.models.enums import Bias, Trend
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.smc import StructureBreak
from atlas.domain.services.swing_detection import find_swing_highs, find_swing_lows
from atlas.domain.services.trend_classification import classify_trend


def detect_structure_breaks(
    bars: list[OHLCVBar],
    swing_lookback: int = 2,
) -> tuple[StructureBreak | None, StructureBreak | None]:
    """Scan bar history and return the most recent BOS and CHoCH."""
    last_bos: StructureBreak | None = None
    last_choch: StructureBreak | None = None

    start = swing_lookback * 2 + 1
    for i in range(start, len(bars)):
        subset = bars[: i + 1]
        trend = classify_trend(subset, swing_lookback)
        highs = find_swing_highs(subset, swing_lookback)
        lows = find_swing_lows(subset, swing_lookback)
        close = bars[i].close

        if trend == Trend.DOWNTREND and highs:
            swing_high = highs[-1][1]
            if close > swing_high:
                last_bos = StructureBreak("bos", Bias.BULLISH, i, swing_high)
                last_choch = StructureBreak("choch", Bias.BULLISH, i, swing_high)

        if trend == Trend.UPTREND and lows:
            swing_low = lows[-1][1]
            if close < swing_low:
                last_bos = StructureBreak("bos", Bias.BEARISH, i, swing_low)
                last_choch = StructureBreak("choch", Bias.BEARISH, i, swing_low)

        if trend == Trend.UPTREND and highs:
            swing_high = highs[-1][1]
            if close > swing_high:
                last_bos = StructureBreak("bos", Bias.BULLISH, i, swing_high)

        if trend == Trend.DOWNTREND and lows:
            swing_low = lows[-1][1]
            if close < swing_low:
                last_bos = StructureBreak("bos", Bias.BEARISH, i, swing_low)

    return last_bos, last_choch


def directional_bias_from_smc(
    trend: Trend,
    last_bos: StructureBreak | None,
    last_choch: StructureBreak | None,
) -> Bias:
    """Derive directional bias for confluence scoring."""
    if last_bos:
        return last_bos.direction
    if last_choch:
        return last_choch.direction
    if trend == Trend.UPTREND:
        return Bias.BULLISH
    if trend == Trend.DOWNTREND:
        return Bias.BEARISH
    return Bias.NEUTRAL
