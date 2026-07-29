"""Bar validation unit tests (Spec 02)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from atlas.domain.models.enums import Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.services.bar_validation import (
    compute_atr,
    is_aligned_open_time,
    is_outlier_bar,
    to_utc,
    validate_ohlc_integrity,
    validate_positive_prices,
)


@pytest.fixture
def instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def _bar(
    instrument: Instrument,
    open_time: datetime,
    o: str,
    h: str,
    low_p: str,
    c: str,
    tf: Timeframe = Timeframe.M15,
) -> OHLCVBar:
    return OHLCVBar(
        instrument=instrument,
        timeframe=tf,
        open_time=open_time,
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(low_p),
        close=Decimal(c),
        volume=Decimal("1000"),
    )


def test_ohlc_integrity_pass(instrument: Instrument) -> None:
    bar = _bar(instrument, datetime(2026, 1, 1, 12, 0, tzinfo=UTC), "100", "105", "99", "103")
    assert validate_ohlc_integrity(bar) is None


def test_ohlc_integrity_fail_high(instrument: Instrument) -> None:
    bar = _bar(instrument, datetime(2026, 1, 1, 12, 0, tzinfo=UTC), "100", "102", "99", "103")
    assert validate_ohlc_integrity(bar) is not None


def test_positive_prices_fail(instrument: Instrument) -> None:
    bar = _bar(instrument, datetime(2026, 1, 1, 12, 0, tzinfo=UTC), "0", "105", "99", "103")
    assert validate_positive_prices(bar) is not None


def test_bar_alignment_m15(instrument: Instrument) -> None:
    assert is_aligned_open_time(datetime(2026, 1, 1, 12, 15, tzinfo=UTC), Timeframe.M15)
    assert not is_aligned_open_time(datetime(2026, 1, 1, 12, 17, tzinfo=UTC), Timeframe.M15)


def test_bar_alignment_h4(instrument: Instrument) -> None:
    assert is_aligned_open_time(datetime(2026, 1, 1, 8, 0, tzinfo=UTC), Timeframe.H4)
    assert not is_aligned_open_time(datetime(2026, 1, 1, 10, 0, tzinfo=UTC), Timeframe.H4)


def test_to_utc_naive() -> None:
    dt = datetime(2026, 1, 1, 12, 0)
    assert to_utc(dt).tzinfo == UTC


def test_compute_atr(instrument: Instrument) -> None:
    bars = []
    for i in range(20):
        bars.append(
            _bar(
                instrument,
                datetime(2026, 1, 1, 12, i, tzinfo=UTC),
                "100",
                "102",
                "99",
                "101",
            )
        )
    atr = compute_atr(bars, 14)
    assert atr is not None
    assert atr > 0


def test_outlier_detection(instrument: Instrument) -> None:
    bar = _bar(instrument, datetime(2026, 1, 1, 12, 0, tzinfo=UTC), "100", "150", "99", "101")
    assert is_outlier_bar(bar, Decimal("2"), Decimal("5")) is True
    assert is_outlier_bar(bar, Decimal("100"), Decimal("5")) is False
