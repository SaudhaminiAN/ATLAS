"""ATR percentile volatility regime classification (Spec 03)."""

from decimal import Decimal

from atlas.domain.models.enums import VolatilityRegime
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.services.bar_validation import compute_atr


def _percentile_value(values: list[Decimal], percentile: float) -> Decimal:
    if not values:
        return Decimal("0")
    sorted_vals = sorted(values)
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    rank = (len(sorted_vals) - 1) * percentile / 100
    lower = int(rank)
    upper = min(lower + 1, len(sorted_vals) - 1)
    weight = Decimal(str(rank - lower))
    return sorted_vals[lower] * (Decimal("1") - weight) + sorted_vals[upper] * weight


def _rolling_atr_series(bars: list[OHLCVBar], period: int) -> list[Decimal]:
    series: list[Decimal] = []
    for end in range(period + 1, len(bars) + 1):
        window = bars[end - period - 1 : end]
        atr = compute_atr(window, period)
        if atr is not None:
            series.append(atr)
    return series


def classify_volatility_regime(
    bars: list[OHLCVBar],
    *,
    atr_period: int = 14,
    lookback: int = 100,
    min_bars_required: int = 100,
) -> tuple[VolatilityRegime, Decimal, Decimal]:
    """Return regime, current ATR, and percentile rank of current ATR."""
    if len(bars) < min_bars_required:
        atr = compute_atr(bars, atr_period) or Decimal("0")
        return VolatilityRegime.NORMAL, atr, Decimal("50")

    atr_series = _rolling_atr_series(bars, atr_period)
    if len(atr_series) < lookback:
        current = atr_series[-1] if atr_series else Decimal("0")
        return VolatilityRegime.NORMAL, current, Decimal("50")

    distribution = atr_series[-lookback:]
    current_atr = distribution[-1]

    p25 = _percentile_value(distribution, 25)
    p75 = _percentile_value(distribution, 75)
    p95 = _percentile_value(distribution, 95)

    rank = _percentile_rank(current_atr, distribution)

    if current_atr <= p25:
        regime = VolatilityRegime.LOW
    elif current_atr <= p75:
        regime = VolatilityRegime.NORMAL
    elif current_atr <= p95:
        regime = VolatilityRegime.HIGH
    else:
        regime = VolatilityRegime.EXTREME

    return regime, current_atr, rank


def _percentile_rank(value: Decimal, distribution: list[Decimal]) -> Decimal:
    below = sum(1 for v in distribution if v < value)
    equal = sum(1 for v in distribution if v == value)
    rank = (below + Decimal("0.5") * equal) / Decimal(len(distribution)) * Decimal("100")
    return rank.quantize(Decimal("0.01"))
