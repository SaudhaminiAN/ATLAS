"""OHLCV bar validation rules (Spec 02)."""

from datetime import UTC, datetime
from decimal import Decimal

from atlas.domain.models.enums import Timeframe
from atlas.domain.models.ohlcv import OHLCVBar

TIMEFRAME_MINUTES: dict[Timeframe, int] = {
    Timeframe.M1: 1,
    Timeframe.M5: 5,
    Timeframe.M15: 15,
    Timeframe.M30: 30,
    Timeframe.H1: 60,
    Timeframe.H4: 240,
    Timeframe.D1: 1440,
}


def to_utc(dt: datetime) -> datetime:
    """Normalize timestamp to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def validate_ohlc_integrity(bar: OHLCVBar) -> str | None:
    """Return error message if OHLC integrity fails."""
    if bar.high < max(bar.open, bar.close):
        return "high < max(open, close)"
    if bar.low > min(bar.open, bar.close):
        return "low > min(open, close)"
    return None


def validate_positive_prices(bar: OHLCVBar) -> str | None:
    """Return error if any price is non-positive."""
    for name, value in (
        ("open", bar.open),
        ("high", bar.high),
        ("low", bar.low),
        ("close", bar.close),
    ):
        if value <= 0:
            return f"{name} must be positive"
    return None


def is_aligned_open_time(open_time: datetime, timeframe: Timeframe) -> bool:
    """Check bar open_time aligns to UTC boundaries per Spec 02."""
    dt = to_utc(open_time)
    if dt.second != 0 or dt.microsecond != 0:
        return False

    minute = dt.minute
    hour = dt.hour

    if timeframe == Timeframe.M1:
        return True
    if timeframe == Timeframe.M5:
        return minute % 5 == 0
    if timeframe == Timeframe.M15:
        return minute in {0, 15, 30, 45}
    if timeframe == Timeframe.M30:
        return minute in {0, 30}
    if timeframe == Timeframe.H1:
        return minute == 0
    if timeframe == Timeframe.H4:
        return minute == 0 and hour % 4 == 0
    if timeframe == Timeframe.D1:
        return minute == 0 and hour == 0
    return False


def compute_atr(bars: list[OHLCVBar], period: int = 14) -> Decimal | None:
    """Compute ATR from prior bars (oldest first)."""
    if len(bars) < period + 1:
        return None

    true_ranges: list[Decimal] = []
    for i in range(1, len(bars)):
        high = bars[i].high
        low = bars[i].low
        prev_close = bars[i - 1].close
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return None

    window = true_ranges[-period:]
    return sum(window) / Decimal(period)


def is_outlier_bar(bar: OHLCVBar, atr: Decimal | None, multiplier: Decimal) -> bool:
    """True if bar range exceeds multiplier × ATR."""
    if atr is None or atr <= 0:
        return False
    bar_range = bar.high - bar.low
    return bar_range > multiplier * atr


def expected_next_open_time(last_open: datetime, timeframe: Timeframe) -> datetime:
    """Calculate expected next bar open time."""
    from datetime import timedelta

    minutes = TIMEFRAME_MINUTES[timeframe]
    return to_utc(last_open) + timedelta(minutes=minutes)
