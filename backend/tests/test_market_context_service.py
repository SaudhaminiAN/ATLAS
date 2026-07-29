"""Market context service tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from atlas.application.market_context.service import MarketContextConfig, MarketContextService
from atlas.domain.models.enums import Timeframe, VolatilityRegime
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def _bars(count: int, instrument: Instrument, tf: Timeframe) -> list[OHLCVBar]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    bars = []
    price = Decimal("2350")
    for i in range(count):
        open_time = start + timedelta(hours=4 * i if tf == Timeframe.H4 else 15 * i)
        bars.append(
            OHLCVBar(
                instrument=instrument,
                timeframe=tf,
                open_time=open_time,
                open=price,
                high=price + Decimal("5"),
                low=price - Decimal("5"),
                close=price + Decimal("1"),
                volume=Decimal("100"),
            )
        )
        price += Decimal("2")
    return bars


@pytest.fixture
def context_service():
    instrument = _instrument()
    primary = _bars(120, instrument, Timeframe.M15)
    bias = _bars(60, instrument, Timeframe.H4)

    market_data = MagicMock()
    market_data.get_instrument = AsyncMock(return_value=instrument)
    market_data.get_recent_bars = AsyncMock(side_effect=[primary, bias])

    bus = InMemoryEventBus()
    events = []
    bus.subscribe("market_context.updated", lambda e: events.append(e))

    cache = MagicMock()
    cache.set_latest = AsyncMock()

    service = MarketContextService(
        market_data_service=market_data,
        event_bus=bus,
        context_cache=cache,
        config=MarketContextConfig(min_bars_required=100),
    )
    return service, instrument, primary, bias, events, cache


def test_compute_is_deterministic(context_service) -> None:
    service, instrument, primary, bias, _, _ = context_service
    as_of = datetime(2026, 1, 15, 14, 0, tzinfo=UTC)
    first = service.compute(instrument, primary, bias, as_of=as_of)
    second = service.compute(instrument, primary, bias, as_of=as_of)
    assert first == second


def test_compute_session_at_overlap(context_service) -> None:
    service, instrument, primary, bias, _, _ = context_service
    as_of = datetime(2026, 1, 15, 14, 0, tzinfo=UTC)
    context = service.compute(instrument, primary, bias, as_of=as_of)
    assert context.primary_session.value == "overlap"


@pytest.mark.asyncio
async def test_analyze_symbol_publishes_event(context_service) -> None:
    service, _, _, _, events, cache = context_service
    context = await service.analyze_symbol("XAUUSD")
    assert context is not None
    cache.set_latest.assert_awaited_once()
    assert len(events) == 1
    assert events[0].event_type == "market_context.updated"


def test_insufficient_bars_uses_normal_volatility(context_service) -> None:
    service, instrument, _, bias, _, _ = context_service
    short_primary = _bars(30, instrument, Timeframe.M15)
    context = service.compute(instrument, short_primary, bias)
    assert context.volatility_regime == VolatilityRegime.NORMAL
