"""Fair value gap detection (Spec 06)."""

from decimal import Decimal

from atlas.domain.models.enums import Bias
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.smc import FairValueGap


def _gap_filled(
    gap_low: Decimal,
    gap_high: Decimal,
    bars_after: list[OHLCVBar],
    fill_pct: Decimal,
) -> bool:
    threshold = gap_low + (gap_high - gap_low) * fill_pct
    for bar in bars_after:
        if bar.low <= threshold <= bar.high:
            return True
        if bar.low <= gap_low and bar.high >= gap_high:
            return True
    return False


def detect_fair_value_gaps(
    bars: list[OHLCVBar],
    *,
    fvg_fill_pct: Decimal = Decimal("0.50"),
) -> list[FairValueGap]:
    """Detect 3-candle FVG patterns."""
    gaps: list[FairValueGap] = []

    for i in range(2, len(bars)):
        first = bars[i - 2]
        third = bars[i]

        if first.high < third.low:
            gap_low = first.high
            gap_high = third.low
            filled = _gap_filled(gap_low, gap_high, bars[i + 1 :], fvg_fill_pct)
            gaps.append(
                FairValueGap(
                    direction=Bias.BULLISH,
                    bar_index=i,
                    gap_low=gap_low,
                    gap_high=gap_high,
                    is_filled=filled,
                )
            )

        if first.low > third.high:
            gap_low = third.high
            gap_high = first.low
            filled = _gap_filled(gap_low, gap_high, bars[i + 1 :], fvg_fill_pct)
            gaps.append(
                FairValueGap(
                    direction=Bias.BEARISH,
                    bar_index=i,
                    gap_low=gap_low,
                    gap_high=gap_high,
                    is_filled=filled,
                )
            )

    return [gap for gap in gaps if not gap.is_filled]
