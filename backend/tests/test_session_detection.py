"""Trading session detection golden tests."""

from datetime import UTC, datetime

import pytest

from atlas.domain.models.enums import TradingSession
from atlas.domain.services.session_detection import detect_sessions


@pytest.mark.parametrize(
    ("hour", "minute", "expected_primary", "expected_active"),
    [
        (7, 59, TradingSession.ASIAN, (TradingSession.ASIAN,)),
        (8, 0, TradingSession.LONDON, (TradingSession.LONDON,)),
        (12, 0, TradingSession.LONDON, (TradingSession.LONDON,)),
        (
            13,
            0,
            TradingSession.OVERLAP,
            (TradingSession.LONDON, TradingSession.NEW_YORK, TradingSession.OVERLAP),
        ),
        (
            15,
            59,
            TradingSession.OVERLAP,
            (TradingSession.LONDON, TradingSession.NEW_YORK, TradingSession.OVERLAP),
        ),
        (16, 0, TradingSession.NEW_YORK, (TradingSession.NEW_YORK,)),
        (21, 59, TradingSession.NEW_YORK, (TradingSession.NEW_YORK,)),
    ],
)
def test_session_boundaries(hour, minute, expected_primary, expected_active) -> None:
    as_of = datetime(2026, 1, 15, hour, minute, tzinfo=UTC)
    primary, active = detect_sessions(as_of)
    assert primary == expected_primary
    assert active == expected_active
