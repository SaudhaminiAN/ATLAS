"""UTC trading session detection (Spec 03)."""

from datetime import datetime, time

from atlas.domain.models.enums import TradingSession
from atlas.domain.services.bar_validation import to_utc

ASIAN_START = time(0, 0)
ASIAN_END = time(8, 0)
LONDON_START = time(8, 0)
LONDON_END = time(16, 0)
NY_START = time(13, 0)
NY_END = time(22, 0)
OVERLAP_START = time(13, 0)
OVERLAP_END = time(16, 0)


def _in_range(t: time, start: time, end: time) -> bool:
    return start <= t < end


def detect_sessions(as_of: datetime) -> tuple[TradingSession, tuple[TradingSession, ...]]:
    """Return primary session and all active sessions at a UTC timestamp."""
    dt = to_utc(as_of)
    t = dt.time()

    active: list[TradingSession] = []
    if _in_range(t, ASIAN_START, ASIAN_END):
        active.append(TradingSession.ASIAN)
    if _in_range(t, LONDON_START, LONDON_END):
        active.append(TradingSession.LONDON)
    if _in_range(t, NY_START, NY_END):
        active.append(TradingSession.NEW_YORK)
    if _in_range(t, OVERLAP_START, OVERLAP_END):
        active.append(TradingSession.OVERLAP)

    if TradingSession.OVERLAP in active:
        primary = TradingSession.OVERLAP
    elif TradingSession.LONDON in active:
        primary = TradingSession.LONDON
    elif TradingSession.NEW_YORK in active:
        primary = TradingSession.NEW_YORK
    elif TradingSession.ASIAN in active:
        primary = TradingSession.ASIAN
    else:
        primary = TradingSession.ASIAN

    return primary, tuple(active)
