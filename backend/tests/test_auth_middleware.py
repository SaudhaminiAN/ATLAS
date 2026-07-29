"""Auth middleware tests."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from atlas.application.container import Container
from atlas.domain.models.user import User
from atlas.infrastructure.config import Settings
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus
from atlas.presentation.api.main import create_app


@pytest.fixture
def auth_settings() -> Settings:
    return Settings(
        jwt_secret="test-secret-key-for-pytest-only-32chars",
        log_json=False,
        database_url="postgresql+asyncpg://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379/0",
        market_data_mock_enabled=False,
        auth_enabled=True,
    )


@pytest.fixture
def auth_app(auth_settings: Settings):
    application = create_app(auth_settings)
    user_id = uuid4()
    now = datetime.now(UTC)
    user = User(
        id=user_id,
        email="trader@example.com",
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    auth_service = MagicMock()
    auth_service.verify_access_token = MagicMock(return_value=user_id)
    auth_service.get_user = AsyncMock(return_value=user)

    decision_engine = MagicMock()
    decision_engine.get_latest = AsyncMock(return_value=None)

    container = Container(
        settings=auth_settings,
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
        position_management_service=MagicMock(),
        ai_explanation_service=MagicMock(),
        auth_service=auth_service,
    )
    application.state.container = container
    application.state.ws_manager = MagicMock()
    return application


@pytest.mark.asyncio
async def test_protected_route_requires_token(auth_app) -> None:
    transport = ASGITransport(app=auth_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/decisions/XAUUSD/latest")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_accepts_bearer_token(auth_app) -> None:
    transport = ASGITransport(app=auth_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/decisions/XAUUSD/latest",
            headers={"Authorization": "Bearer valid-token"},
        )

    assert response.status_code == 200
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_health_stays_public_when_auth_enabled(auth_app) -> None:
    transport = ASGITransport(app=auth_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["data"]["auth_enabled"] is True
