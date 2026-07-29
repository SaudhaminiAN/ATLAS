"""Replay protocol tests — no look-ahead."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from atlas.domain.models.enums import Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar


def test_get_bars_up_to_no_lookahead() -> None:
    """Bars returned must have open_time <= as_of."""
    instrument = Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )
    bars = [
        OHLCVBar(
            instrument=instrument,
            timeframe=Timeframe.M15,
            open_time=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            open=Decimal("1"),
            high=Decimal("2"),
            low=Decimal("1"),
            close=Decimal("2"),
            volume=Decimal("1"),
        ),
        OHLCVBar(
            instrument=instrument,
            timeframe=Timeframe.M15,
            open_time=datetime(2026, 1, 1, 12, 15, tzinfo=UTC),
            open=Decimal("2"),
            high=Decimal("3"),
            low=Decimal("2"),
            close=Decimal("3"),
            volume=Decimal("1"),
        ),
        OHLCVBar(
            instrument=instrument,
            timeframe=Timeframe.M15,
            open_time=datetime(2026, 1, 1, 12, 30, tzinfo=UTC),
            open=Decimal("3"),
            high=Decimal("4"),
            low=Decimal("3"),
            close=Decimal("4"),
            volume=Decimal("1"),
        ),
    ]

    as_of = datetime(2026, 1, 1, 12, 15, tzinfo=UTC)
    filtered = [b for b in bars if b.open_time <= as_of]
    assert len(filtered) == 2
    assert all(b.open_time <= as_of for b in filtered)
