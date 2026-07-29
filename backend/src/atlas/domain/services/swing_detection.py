"""Swing point detection (2-bar rule, shared with Spec 05/06)."""

from decimal import Decimal

from atlas.domain.models.ohlcv import OHLCVBar


def find_swing_highs(bars: list[OHLCVBar], lookback: int = 2) -> list[tuple[int, Decimal]]:
    """Return (bar_index, high) for confirmed swing highs; excludes last `lookback` bars."""
    if len(bars) < lookback * 2 + 1:
        return []

    swings: list[tuple[int, Decimal]] = []
    last_valid = len(bars) - lookback - 1

    for i in range(lookback, last_valid + 1):
        high = bars[i].high
        is_swing = True
        for offset in range(1, lookback + 1):
            if high <= bars[i - offset].high or high <= bars[i + offset].high:
                is_swing = False
                break
        if is_swing:
            swings.append((i, high))

    return swings


def find_swing_lows(bars: list[OHLCVBar], lookback: int = 2) -> list[tuple[int, Decimal]]:
    """Return (bar_index, low) for confirmed swing lows; excludes last `lookback` bars."""
    if len(bars) < lookback * 2 + 1:
        return []

    swings: list[tuple[int, Decimal]] = []
    last_valid = len(bars) - lookback - 1

    for i in range(lookback, last_valid + 1):
        low = bars[i].low
        is_swing = True
        for offset in range(1, lookback + 1):
            if low >= bars[i - offset].low or low >= bars[i + offset].low:
                is_swing = False
                break
        if is_swing:
            swings.append((i, low))

    return swings
