"""Shared domain enumerations."""

from enum import StrEnum


class Direction(StrEnum):
    """Trade or evidence direction."""

    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"


class Bias(StrEnum):
    """Structural or analytical bias without commitment to trade."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class Timeframe(StrEnum):
    """Supported OHLCV timeframes."""

    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"


class TradingSession(StrEnum):
    """UTC trading sessions for XAUUSD context."""

    ASIAN = "asian"
    LONDON = "london"
    NEW_YORK = "new_york"
    OVERLAP = "overlap"


class VolatilityRegime(StrEnum):
    """ATR percentile bucket."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"


class SpreadStatus(StrEnum):
    """Bid-ask spread assessment."""

    NORMAL = "normal"
    ELEVATED = "elevated"


class Trend(StrEnum):
    """Structural trend classification."""

    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    RANGING = "ranging"
