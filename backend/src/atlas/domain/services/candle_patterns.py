"""Candlestick pattern detection (Spec 07)."""

from decimal import Decimal

from atlas.domain.models.enums import Bias
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.price_action import CandlePattern
from atlas.domain.services.bar_validation import compute_atr


def _body_size(bar: OHLCVBar) -> Decimal:
    return abs(bar.close - bar.open)


def _range_size(bar: OHLCVBar) -> Decimal:
    return bar.high - bar.low


def _lower_wick(bar: OHLCVBar) -> Decimal:
    return min(bar.open, bar.close) - bar.low


def _upper_wick(bar: OHLCVBar) -> Decimal:
    return bar.high - max(bar.open, bar.close)


def _is_bullish(bar: OHLCVBar) -> bool:
    return bar.close > bar.open


def _is_bearish(bar: OHLCVBar) -> bool:
    return bar.close < bar.open


def detect_pin_bar(bar: OHLCVBar, bar_index: int) -> CandlePattern | None:
    """Detect bullish or bearish pin bar on a single closed bar."""
    candle_range = _range_size(bar)
    if candle_range == 0:
        return None

    body = _body_size(bar)
    lower_wick = _lower_wick(bar)
    upper_wick = _upper_wick(bar)

    if lower_wick >= Decimal("0.66") * candle_range and body <= Decimal("0.33") * candle_range:
        return CandlePattern(
            pattern_type="pin_bar",
            direction=Bias.BULLISH,
            bar_index=bar_index,
            strength=Decimal("0.55"),
            at_key_level=False,
        )

    if upper_wick >= Decimal("0.66") * candle_range and body <= Decimal("0.33") * candle_range:
        return CandlePattern(
            pattern_type="pin_bar",
            direction=Bias.BEARISH,
            bar_index=bar_index,
            strength=Decimal("0.55"),
            at_key_level=False,
        )

    return None


def detect_engulfing(prev: OHLCVBar, curr: OHLCVBar, bar_index: int) -> CandlePattern | None:
    """Detect bullish or bearish engulfing between two closed bars."""
    if _is_bearish(prev) and _is_bullish(curr):
        if curr.open <= prev.close and curr.close >= prev.open:
            return CandlePattern(
                pattern_type="engulfing",
                direction=Bias.BULLISH,
                bar_index=bar_index,
                strength=Decimal("0.65"),
                at_key_level=False,
            )

    if _is_bullish(prev) and _is_bearish(curr):
        if curr.open >= prev.close and curr.close <= prev.open:
            return CandlePattern(
                pattern_type="engulfing",
                direction=Bias.BEARISH,
                bar_index=bar_index,
                strength=Decimal("0.65"),
                at_key_level=False,
            )

    return None


def detect_inside_bar(prev: OHLCVBar, curr: OHLCVBar, bar_index: int) -> CandlePattern | None:
    """Detect inside bar relative to the prior closed bar."""
    if curr.high < prev.high and curr.low > prev.low:
        direction = Bias.BULLISH if _is_bullish(curr) else Bias.BEARISH
        if curr.close == curr.open:
            direction = Bias.NEUTRAL
        return CandlePattern(
            pattern_type="inside_bar",
            direction=direction,
            bar_index=bar_index,
            strength=Decimal("0.50"),
            at_key_level=False,
        )
    return None


def detect_displacement(
    bars: list[OHLCVBar],
    bar_index: int,
    *,
    displacement_atr_multiplier: Decimal = Decimal("1.5"),
    atr_period: int = 14,
) -> CandlePattern | None:
    """Detect displacement candle using ATR body threshold."""
    if bar_index < atr_period:
        return None

    bar = bars[bar_index]
    body = _body_size(bar)
    if body == 0:
        return None

    atr = compute_atr(bars[: bar_index + 1], atr_period)
    if atr is None or atr <= 0:
        return None

    if body < displacement_atr_multiplier * atr:
        return None

    if _is_bullish(bar):
        direction = Bias.BULLISH
    elif _is_bearish(bar):
        direction = Bias.BEARISH
    else:
        return None

    return CandlePattern(
        pattern_type="displacement",
        direction=direction,
        bar_index=bar_index,
        strength=Decimal("0.70"),
        at_key_level=False,
    )


def detect_patterns_on_closed_bar(
    bars: list[OHLCVBar],
    *,
    displacement_atr_multiplier: Decimal = Decimal("1.5"),
) -> list[CandlePattern]:
    """Detect all patterns on the most recently closed bar."""
    if len(bars) < 3:
        return []

    bar_index = len(bars) - 1
    curr = bars[bar_index]
    prev = bars[bar_index - 1]
    patterns: list[CandlePattern] = []

    pin = detect_pin_bar(curr, bar_index)
    if pin:
        patterns.append(pin)

    engulfing = detect_engulfing(prev, curr, bar_index)
    if engulfing:
        patterns.append(engulfing)

    inside = detect_inside_bar(prev, curr, bar_index)
    if inside and inside.direction != Bias.NEUTRAL:
        patterns.append(inside)

    displacement = detect_displacement(
        bars,
        bar_index,
        displacement_atr_multiplier=displacement_atr_multiplier,
    )
    if displacement:
        patterns.append(displacement)

    return patterns
