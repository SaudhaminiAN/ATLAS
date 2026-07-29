"""Volatility regime classification tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from atlas.domain.models.enums import Timeframe, VolatilityRegime
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.services.volatility_regime import classify_volatility_regime


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def _make_bars(count: int, *, range_size: Decimal = Decimal("2")) -> list[OHLCVBar]:
    instrument = _instrument()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    bars: list[OHLCVBar] = []
    price = Decimal("2350")

    for i in range(count):
        open_time = start + timedelta(minutes=15 * i)
        high = price + range_size
        low = price - range_size
        bars.append(
            OHLCVBar(
                instrument=instrument,
                timeframe=Timeframe.M15,
                open_time=open_time,
                open=price,
                high=high,
                low=low,
                close=price + Decimal("0.1"),
                volume=Decimal("100"),
            )
        )
        price += Decimal("0.05")

    return bars


def test_insufficient_bars_returns_normal() -> None:
    bars = _make_bars(50)
    regime, _, percentile = classify_volatility_regime(bars, min_bars_required=100)
    assert regime == VolatilityRegime.NORMAL
    assert percentile == Decimal("50")


def test_extreme_regime_above_95th_percentile() -> None:
    calm = _make_bars(120, range_size=Decimal("1"))
    volatile_tail = _make_bars(5, range_size=Decimal("50"))
    bars = calm + volatile_tail

    regime, _, _ = classify_volatility_regime(
        bars,
        atr_period=14,
        lookback=100,
        min_bars_required=100,
    )
    assert regime == VolatilityRegime.EXTREME


def test_same_bars_same_regime() -> None:
    bars = _make_bars(130, range_size=Decimal("3"))
    first = classify_volatility_regime(bars)
    second = classify_volatility_regime(bars)
    assert first == second
