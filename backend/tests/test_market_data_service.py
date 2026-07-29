"""Market data service tests with in-memory fakes."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from atlas.application.market_data.service import MarketDataConfig, MarketDataService
from atlas.domain.models.enums import Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import IngestStatus, OHLCVBar
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus


@pytest.fixture
def instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


class FakeBarCache:
    async def set_latest(self, bar: OHLCVBar) -> None:
        self.latest = bar

    async def get_latest(self, symbol: str, timeframe: Timeframe) -> dict | None:
        return None


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def commit(self):
        pass


class FakeOHLCVRepo:
    def __init__(self) -> None:
        self.bars: list[OHLCVBar] = []

    async def exists(self, instrument_id, timeframe, open_time) -> bool:
        return any(b.open_time == open_time for b in self.bars)

    async def get_latest(self, instrument_id, timeframe):
        matching = [b for b in self.bars if b.timeframe == timeframe]
        return matching[-1] if matching else None

    async def get_bars_before(self, instrument_id, timeframe, before, limit):
        return []

    async def insert(self, bar: OHLCVBar) -> bool:
        if any(b.open_time == bar.open_time for b in self.bars):
            return False
        self.bars.append(bar)
        return True

    async def get_history(self, instrument_id, timeframe, start, end, limit):
        return self.bars


@pytest.fixture
def service(monkeypatch) -> tuple[MarketDataService, InMemoryEventBus, FakeOHLCVRepo]:
    bus = InMemoryEventBus()
    cache = FakeBarCache()
    repo = FakeOHLCVRepo()

    def session_factory():
        return FakeSession()

    svc = MarketDataService(
        session_factory=session_factory,  # type: ignore[arg-type]
        event_bus=bus,
        bar_cache=cache,  # type: ignore[arg-type]
        config=MarketDataConfig(),
    )

    async def fake_exists(*args, **kwargs):
        return await repo.exists(*args, **kwargs)

    monkeypatch.setattr(
        "atlas.application.market_data.service.OHLCVBarRepository",
        lambda session: repo,
    )
    return svc, bus, repo


@pytest.mark.asyncio
async def test_ingest_rejects_forming_bar(service, instrument) -> None:
    svc, _, _ = service
    bar = OHLCVBar(
        instrument=instrument,
        timeframe=Timeframe.M15,
        open_time=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        open=Decimal("100"),
        high=Decimal("105"),
        low=Decimal("99"),
        close=Decimal("103"),
        volume=Decimal("100"),
    )
    result = await svc.ingest_bar(bar, is_closed=False)
    assert result.status == IngestStatus.REJECTED
    assert result.rule == "closed_bar_only"


@pytest.mark.asyncio
async def test_ingest_accepts_valid_bar(service, instrument) -> None:
    svc, bus, repo = service
    events: list[str] = []
    bus.subscribe("market_data.bar.received", lambda e: events.append(e.event_type))

    bar = OHLCVBar(
        instrument=instrument,
        timeframe=Timeframe.M15,
        open_time=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        open=Decimal("2350"),
        high=Decimal("2355"),
        low=Decimal("2348"),
        close=Decimal("2352"),
        volume=Decimal("1000"),
    )
    result = await svc.ingest_bar(bar, is_closed=True)
    assert result.status == IngestStatus.ACCEPTED
    assert len(repo.bars) == 1
    assert events == ["market_data.bar.received"]


@pytest.mark.asyncio
async def test_ingest_rejects_invalid_ohlc(service, instrument) -> None:
    svc, _, repo = service
    bar = OHLCVBar(
        instrument=instrument,
        timeframe=Timeframe.M15,
        open_time=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        open=Decimal("2350"),
        high=Decimal("2340"),
        low=Decimal("2348"),
        close=Decimal("2352"),
        volume=Decimal("1000"),
    )
    result = await svc.ingest_bar(bar, is_closed=True)
    assert result.status == IngestStatus.REJECTED
    assert len(repo.bars) == 0


@pytest.mark.asyncio
async def test_mock_provider_fetch_bars(instrument) -> None:
    from atlas.infrastructure.market_data.mock_provider import MockMarketDataProvider

    provider = MockMarketDataProvider()
    start = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    end = datetime(2026, 1, 1, 4, 0, tzinfo=UTC)
    bars = await provider.fetch_bars(instrument, Timeframe.H1, start, end)
    assert len(bars) >= 4
    assert all(b.instrument.symbol == "XAUUSD" for b in bars)
