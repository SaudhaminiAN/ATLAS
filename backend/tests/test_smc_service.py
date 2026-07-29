"""SMC application service tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from atlas.application.smc.service import SmartMoneyConceptsService, SMCConfig
from atlas.domain.events.base import DomainEvent
from atlas.domain.models.enums import Bias, Timeframe, Trend
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


def _bars(count: int) -> list[OHLCVBar]:
    instrument = _instrument()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    bars = []
    price = Decimal("2350")
    for i in range(count):
        bars.append(
            OHLCVBar(
                instrument=instrument,
                timeframe=Timeframe.M15,
                open_time=start + timedelta(minutes=15 * i),
                open=price,
                high=price + Decimal("10"),
                low=price - Decimal("8"),
                close=price + Decimal("2"),
                volume=Decimal("100"),
            )
        )
        price += Decimal("0.5")
    return bars


@pytest.fixture
def smc_service():
    market_data = MagicMock()
    market_data.get_instrument = AsyncMock(return_value=_instrument())
    market_data.get_recent_bars = AsyncMock(return_value=_bars(80))

    bus = InMemoryEventBus()
    events: list[DomainEvent] = []
    bus.subscribe("analysis.smc.completed", lambda e: events.append(e))

    service = SmartMoneyConceptsService(
        market_data_service=market_data,
        event_bus=bus,
        config=SMCConfig(min_bars=50, bar_lookback=80),
    )
    return service, events


def test_analyze_does_not_emit_trade_signal(smc_service) -> None:
    service, _ = smc_service
    result = service.analyze(_instrument(), Timeframe.M15, _bars(80))
    assert not hasattr(result, "direction")
    assert result.directional_bias in (Bias.BULLISH, Bias.BEARISH, Bias.NEUTRAL)


def test_analyze_is_deterministic(smc_service) -> None:
    service, _ = smc_service
    instrument = _instrument()
    bars = _bars(80)
    first = service.analyze(instrument, Timeframe.M15, bars)
    second = service.analyze(instrument, Timeframe.M15, bars)
    assert first == second


def test_insufficient_bars_returns_neutral(smc_service) -> None:
    service, _ = smc_service
    result = service.analyze(_instrument(), Timeframe.M15, _bars(10))
    assert result.trend == Trend.RANGING
    assert result.directional_bias == Bias.NEUTRAL
    assert result.last_bos is None
    assert result.last_choch is None


@pytest.mark.asyncio
async def test_analyze_symbol_publishes_event(smc_service) -> None:
    service, events = smc_service
    result = await service.analyze_symbol("XAUUSD")
    assert result is not None
    assert len(events) == 1
    assert events[0].event_type == "analysis.smc.completed"
    assert events[0].payload["symbol"] == "XAUUSD"
