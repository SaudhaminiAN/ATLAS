"""SMC domain golden tests (Spec 06)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from atlas.domain.models.enums import Bias, Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.services.fair_value_gaps import detect_fair_value_gaps
from atlas.domain.services.order_blocks import detect_order_blocks
from atlas.domain.services.smc_structure import detect_structure_breaks
from atlas.domain.services.swing_detection import find_swing_highs


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def _bar(
    i: int,
    *,
    open_: Decimal,
    high: Decimal,
    low: Decimal,
    close: Decimal,
    instrument: Instrument | None = None,
) -> OHLCVBar:
    instrument = instrument or _instrument()
    return OHLCVBar(
        instrument=instrument,
        timeframe=Timeframe.M15,
        open_time=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=15 * i),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=Decimal("100"),
    )


def _flat_bars(count: int, price: Decimal = Decimal("100")) -> list[OHLCVBar]:
    return [
        _bar(
            i,
            open_=price,
            high=price + Decimal("1"),
            low=price - Decimal("1"),
            close=price,
        )
        for i in range(count)
    ]


def test_swing_highs_exclude_last_two_bars() -> None:
    highs = [Decimal(v) for v in [10, 12, 20, 14, 11, 15, 18, 13, 10, 9]]
    bars = [
        _bar(i, open_=h, high=h, low=h - Decimal("2"), close=h)
        for i, h in enumerate(highs)
    ]
    swings = find_swing_highs(bars, lookback=2)
    assert all(index < len(bars) - 2 for index, _ in swings)


def test_bullish_fvg_detected() -> None:
    bars = [
        _bar(
            0,
            open_=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
        ),
        _bar(
            1,
            open_=Decimal("102"),
            high=Decimal("103"),
            low=Decimal("101"),
            close=Decimal("102"),
        ),
        _bar(
            2,
            open_=Decimal("106"),
            high=Decimal("107"),
            low=Decimal("105"),
            close=Decimal("106"),
        ),
    ]
    gaps = detect_fair_value_gaps(bars)
    assert len(gaps) == 1
    assert gaps[0].direction == Bias.BULLISH
    assert gaps[0].gap_low == Decimal("101")
    assert gaps[0].gap_high == Decimal("105")


def test_bearish_fvg_detected() -> None:
    bars = [
        _bar(
            0,
            open_=Decimal("110"),
            high=Decimal("111"),
            low=Decimal("109"),
            close=Decimal("110"),
        ),
        _bar(
            1,
            open_=Decimal("108"),
            high=Decimal("109"),
            low=Decimal("107"),
            close=Decimal("108"),
        ),
        _bar(
            2,
            open_=Decimal("104"),
            high=Decimal("105"),
            low=Decimal("103"),
            close=Decimal("104"),
        ),
    ]
    gaps = detect_fair_value_gaps(bars)
    assert len(gaps) == 1
    assert gaps[0].direction == Bias.BEARISH
    assert gaps[0].gap_low == Decimal("105")
    assert gaps[0].gap_high == Decimal("109")


def test_bullish_order_block_detected() -> None:
    bars = _flat_bars(20)
    bars.append(
        _bar(20, open_=Decimal("102"), high=Decimal("103"), low=Decimal("97"), close=Decimal("98"))
    )
    bars.append(
        _bar(21, open_=Decimal("98"), high=Decimal("115"), low=Decimal("97"), close=Decimal("114"))
    )
    blocks = detect_order_blocks(bars)
    assert len(blocks) >= 1
    assert blocks[-1].direction == Bias.BULLISH
    assert blocks[-1].bar_index == 20
    assert blocks[-1].is_mitigated is False


def test_bullish_bos_detected_in_downtrend() -> None:
    instrument = _instrument()
    bars: list[OHLCVBar] = []
    for i in range(30):
        phase = i // 5
        base = Decimal("200") - Decimal(phase * 8)
        swing = Decimal(i % 5)
        high = base + swing + Decimal("4")
        low = base + swing
        close = base + swing + Decimal("1")
        bars.append(
            _bar(
                i,
                open_=close,
                high=high,
                low=low,
                close=close,
                instrument=instrument,
            )
        )

    break_price = bars[-1].high + Decimal("20")
    bars.append(
        _bar(
            30,
            open_=bars[-1].close,
            high=break_price,
            low=bars[-1].low,
            close=break_price - Decimal("1"),
            instrument=instrument,
        )
    )

    last_bos, _ = detect_structure_breaks(bars)
    assert last_bos is not None
    assert last_bos.break_type == "bos"
    assert last_bos.direction == Bias.BULLISH
