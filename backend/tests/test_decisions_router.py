"""Decision REST endpoint tests."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from atlas.application.container import Container
from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.enums import Direction
from atlas.domain.models.instrument import Instrument
from atlas.infrastructure.config import Settings
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus
from atlas.presentation.api.main import create_app


@pytest.fixture
def app():
    """FastAPI app with mocked decision service."""
    settings = Settings(
        jwt_secret="test-secret-key-for-pytest-only-32chars",
        log_json=False,
        database_url="postgresql+asyncpg://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379/0",
        market_data_mock_enabled=False,
    )
    application = create_app(settings)

    instrument = Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )
    decision = TradingDecision(
        id=uuid4(),
        instrument=instrument,
        direction=Direction.WAIT,
        is_actionable=False,
        confluence_score=Decimal("0.55"),
        strategy_id="test",
        reason="Confluence below threshold",
        correlation_id="cid-1",
        decided_at=datetime.now(UTC),
    )

    decision_engine = MagicMock()
    decision_engine.get_latest = AsyncMock(return_value=decision)
    decision_engine.get_history = AsyncMock(return_value=[decision])

    application.state.container = Container(
        settings=settings,
        event_bus=InMemoryEventBus(),
        engine=MagicMock(),
        session_factory=MagicMock(),
        redis=AsyncMock(),
        pipeline=MagicMock(),
        market_data_service=MagicMock(),
        market_data_replay=MagicMock(),
        mock_provider=MagicMock(),
        bar_cache=MagicMock(),
        strategy_engine=MagicMock(),
        news_filter=MagicMock(),
        market_context_service=MagicMock(),
        mtf_service=MagicMock(),
        technical_analysis_service=MagicMock(),
        smc_service=MagicMock(),
        price_action_service=MagicMock(),
        confluence_service=MagicMock(),
        trade_validation_service=MagicMock(),
        decision_engine=decision_engine,
        journal_service=MagicMock(),
        backtest_runner=MagicMock(),
        analytics_service=MagicMock(),
        risk_management_service=MagicMock(),
        execution_service=MagicMock(),
    )
    application.state.ws_manager = MagicMock()
    return application


@pytest.mark.asyncio
async def test_get_latest_decision(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/decisions/XAUUSD/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["symbol"] == "XAUUSD"
    assert body["data"]["direction"] == "WAIT"
    assert body["data"]["reason"] == "Confluence below threshold"


@pytest.mark.asyncio
async def test_get_latest_decision_not_found(app) -> None:
    app.state.container.decision_engine.get_latest = AsyncMock(return_value=None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/decisions/XAUUSD/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_get_decision_history(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/decisions/XAUUSD/history?limit=10")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) == 1
