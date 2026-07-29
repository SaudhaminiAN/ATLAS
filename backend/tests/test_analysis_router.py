"""Analysis API endpoint tests."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from atlas.application.container import Container
from atlas.domain.models.enums import (
    Bias,
    SpreadStatus,
    TradingSession,
    VolatilityRegime,
)
from atlas.domain.models.market_context import MarketContext
from atlas.infrastructure.config import Settings
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus
from atlas.presentation.api.main import create_app


def _sample_context():
    instrument = MagicMock()
    instrument.symbol = "XAUUSD"
    return MarketContext(
        instrument=instrument,
        primary_session=TradingSession.OVERLAP,
        active_sessions=(TradingSession.OVERLAP, TradingSession.LONDON),
        volatility_regime=VolatilityRegime.NORMAL,
        spread_status=SpreadStatus.NORMAL,
        structural_bias=Bias.NEUTRAL,
        atr_value=Decimal("2.5"),
        atr_percentile=Decimal("45.00"),
        computed_at=datetime.now(UTC),
    )


@pytest.fixture
def app():
    settings = Settings(
        jwt_secret="test-secret-key-for-pytest-only-32chars",
        log_json=False,
        database_url="postgresql+asyncpg://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379/0",
        market_data_mock_enabled=False,
        news_mock_enabled=False,
    )
    application = create_app(settings)
    market_context_service = MagicMock()
    market_context_service.get_cached = AsyncMock(return_value=_sample_context())
    market_context_service.analyze_symbol = AsyncMock(return_value=_sample_context())

    application.state.container = Container(
        settings=settings,
        event_bus=InMemoryEventBus(),
        engine=MagicMock(),
        session_factory=MagicMock(),
        redis=MagicMock(),
        pipeline=MagicMock(),
        market_data_service=MagicMock(),
        market_data_replay=MagicMock(),
        mock_provider=MagicMock(),
        bar_cache=MagicMock(),
        strategy_engine=MagicMock(),
        news_filter=MagicMock(),
        market_context_service=market_context_service,
    )
    application.state.ws_manager = MagicMock()
    return application


@pytest.mark.asyncio
async def test_get_market_context(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/analysis/XAUUSD/context")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["primary_session"] == "overlap"
    assert body["data"]["volatility_regime"] == "normal"
