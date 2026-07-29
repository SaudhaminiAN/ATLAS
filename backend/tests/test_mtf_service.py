"""MTF service tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from atlas.application.mtf.service import MTFConfig, MultiTimeframeAnalysisService
from atlas.domain.events.base import DomainEvent
from atlas.domain.models.enums import Direction, Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.strategy import StrategyProfile
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def _bars(count: int, tf: Timeframe) -> list[OHLCVBar]:
    instrument = _instrument()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    highs = [10, 11, 15, 12, 11, 13, 18, 14, 13, 16, 22, 17, 16, 20, 26]
    lows = [5, 6, 7, 6, 5, 7, 9, 8, 7, 9, 11, 10, 9, 12, 14]
    bars = []
    for i in range(count):
        h = Decimal(highs[i % len(highs)])
        low = Decimal(lows[i % len(lows)])
        delta = timedelta(hours=4) if tf == Timeframe.H4 else timedelta(minutes=15)
        bars.append(
            OHLCVBar(
                instrument=instrument,
                timeframe=tf,
                open_time=start + delta * i,
                open=(h + low) / 2,
                high=h,
                low=low,
                close=(h + low) / 2,
                volume=Decimal("100"),
            )
        )
    return bars


@pytest.fixture
def mtf_service():
    instrument = _instrument()
    strategy = StrategyProfile(
        id="test",
        name="Test",
        min_confluence_score=Decimal("0.7"),
        enabled_directions=(Direction.BUY, Direction.SELL),
        confluence_weights={"mtf_alignment": Decimal("0.25")},
        active_timeframes=(Timeframe.D1, Timeframe.H4, Timeframe.H1, Timeframe.M15),
        allowed_sessions=(),
        validation_rule_flags={},
        is_active=True,
        updated_at=datetime.now(UTC),
    )

    market_data = MagicMock()
    market_data.get_instrument = AsyncMock(return_value=instrument)
    market_data.get_recent_bars = AsyncMock(
        side_effect=lambda inst, tf, limit, as_of=None: _bars(60, tf)
    )

    strategy_engine = MagicMock()
    strategy_engine.get_active = AsyncMock(return_value=strategy)

    bus = InMemoryEventBus()
    events: list[DomainEvent] = []
    bus.subscribe("analysis.mtf.completed", lambda e: events.append(e))

    service = MultiTimeframeAnalysisService(
        market_data_service=market_data,
        strategy_engine=strategy_engine,
        event_bus=bus,
        config=MTFConfig(min_bars=50),
    )
    return service, events


@pytest.mark.asyncio
async def test_analyze_symbol_publishes_event(mtf_service) -> None:
    service, events = mtf_service
    result = await service.analyze_symbol("XAUUSD")
    assert result is not None
    assert len(result.biases) == 4
    assert len(events) == 1
    assert events[0].event_type == "analysis.mtf.completed"


def test_analyze_is_deterministic(mtf_service) -> None:
    service, _ = mtf_service
    instrument = _instrument()
    bars = {
        Timeframe.H4: _bars(60, Timeframe.H4),
        Timeframe.M15: _bars(60, Timeframe.M15),
    }
    strategy = StrategyProfile(
        id="test",
        name="Test",
        min_confluence_score=Decimal("0.7"),
        enabled_directions=(Direction.BUY,),
        confluence_weights={},
        active_timeframes=(Timeframe.H4, Timeframe.M15),
        allowed_sessions=(),
        validation_rule_flags={},
        is_active=True,
        updated_at=datetime.now(UTC),
    )
    as_of = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    first = service.analyze(instrument, bars, {}, {}, strategy, computed_at=as_of)
    second = service.analyze(instrument, bars, {}, {}, strategy, computed_at=as_of)
    assert first == second
