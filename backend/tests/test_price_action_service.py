"""Price action service tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from atlas.application.price_action.service import PriceActionConfig, PriceActionService
from atlas.domain.events.base import DomainEvent
from atlas.domain.models.enums import Bias, Timeframe, Trend
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.smc import SMCAnalysisResult
from atlas.domain.models.technical import TechnicalAnalysisResult
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


def _smc(instrument: Instrument) -> SMCAnalysisResult:
    return SMCAnalysisResult(
        instrument=instrument,
        timeframe=Timeframe.M15,
        trend=Trend.RANGING,
        last_bos=None,
        last_choch=None,
        order_blocks=(),
        liquidity_pools=(),
        fair_value_gaps=(),
        directional_bias=Bias.NEUTRAL,
        computed_at=datetime.now(UTC),
    )


@pytest.fixture
def price_action_service():
    market_data = MagicMock()
    instrument = _instrument()
    bars = _bars(80)
    market_data.get_instrument = AsyncMock(return_value=instrument)
    market_data.get_recent_bars = AsyncMock(return_value=bars)

    technical = MagicMock()
    technical.analyze = MagicMock(
        return_value=TechnicalAnalysisResult(
            instrument=instrument,
            timeframe=Timeframe.M15,
            trend=Trend.UPTREND,
            key_levels=(),
            nearest_support=None,
            nearest_resistance=None,
            indicator_context={},
            bullish_context_score=Decimal("0.3"),
            bearish_context_score=Decimal("0.1"),
            computed_at=datetime.now(UTC),
        )
    )

    smc = MagicMock()
    smc.analyze = MagicMock(return_value=_smc(instrument))

    bus = InMemoryEventBus()
    events: list[DomainEvent] = []
    bus.subscribe("analysis.price_action.completed", lambda e: events.append(e))

    service = PriceActionService(
        market_data_service=market_data,
        technical_analysis_service=technical,
        smc_service=smc,
        event_bus=bus,
        config=PriceActionConfig(min_bars=3, bar_lookback=80),
    )
    return service, events, instrument, bars


def test_insufficient_bars_returns_empty(price_action_service) -> None:
    service, _, instrument, _ = price_action_service
    result = service.analyze(instrument, Timeframe.M15, _bars(2), [], _smc(instrument))
    assert result.patterns == ()
    assert result.strongest_pattern is None


def test_analyze_is_deterministic(price_action_service) -> None:
    service, _, instrument, bars = price_action_service
    smc = _smc(instrument)
    computed_at = datetime(2026, 1, 1, tzinfo=UTC)
    first = service.analyze(instrument, Timeframe.M15, bars, [], smc, computed_at=computed_at)
    second = service.analyze(instrument, Timeframe.M15, bars, [], smc, computed_at=computed_at)
    assert first == second


@pytest.mark.asyncio
async def test_analyze_symbol_publishes_event(price_action_service) -> None:
    service, events, _, _ = price_action_service
    result = await service.analyze_symbol("XAUUSD")
    assert result is not None
    assert len(events) == 1
    assert events[0].event_type == "analysis.price_action.completed"
