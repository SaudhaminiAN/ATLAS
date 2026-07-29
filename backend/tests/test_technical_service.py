"""Technical analysis service tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from atlas.application.technical.service import TechnicalAnalysisConfig, TechnicalAnalysisService
from atlas.domain.events.base import DomainEvent
from atlas.domain.models.enums import Timeframe, Trend
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
    highs = [10, 11, 15, 12, 11, 13, 18, 14, 13, 16, 22, 17, 16, 20, 26]
    lows = [5, 6, 7, 6, 5, 7, 9, 8, 7, 9, 11, 10, 9, 12, 14]
    bars = []
    price = Decimal("2350")
    for i in range(count):
        h = Decimal(highs[i % len(highs)])
        low = Decimal(lows[i % len(lows)])
        bars.append(
            OHLCVBar(
                instrument=instrument,
                timeframe=Timeframe.M15,
                open_time=start + timedelta(minutes=15 * i),
                open=price,
                high=price + h,
                low=price - low,
                close=price + Decimal("1"),
                volume=Decimal("100"),
            )
        )
        price += Decimal("0.5")
    return bars


@pytest.fixture
def technical_service():
    market_data = MagicMock()
    market_data.get_instrument = AsyncMock(return_value=_instrument())
    market_data.get_recent_bars = AsyncMock(return_value=_bars(220))

    bus = InMemoryEventBus()
    events: list[DomainEvent] = []
    bus.subscribe("analysis.technical.completed", lambda e: events.append(e))

    service = TechnicalAnalysisService(
        market_data_service=market_data,
        event_bus=bus,
        config=TechnicalAnalysisConfig(min_bars=200),
    )
    return service, events


def test_analyze_does_not_return_trade_direction(technical_service) -> None:
    service, _ = technical_service
    result = service.analyze(_instrument(), Timeframe.M15, _bars(220))
    assert not hasattr(result, "direction")
    assert result.bullish_context_score <= Decimal("0.5")
    assert result.bearish_context_score <= Decimal("0.5")


def test_analyze_is_deterministic(technical_service) -> None:
    service, _ = technical_service
    instrument = _instrument()
    bars = _bars(220)
    as_of = datetime(2026, 6, 1, tzinfo=UTC)
    first = service.analyze(instrument, Timeframe.M15, bars, computed_at=as_of)
    second = service.analyze(instrument, Timeframe.M15, bars, computed_at=as_of)
    assert first == second


@pytest.mark.asyncio
async def test_analyze_symbol_publishes_event(technical_service) -> None:
    service, events = technical_service
    result = await service.analyze_symbol("XAUUSD")
    assert result is not None
    assert result.trend in {Trend.UPTREND, Trend.DOWNTREND, Trend.RANGING}
    assert len(events) == 1
    assert events[0].event_type == "analysis.technical.completed"
