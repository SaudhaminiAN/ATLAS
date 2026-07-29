"""Auth router tests."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from atlas.application.auth.service import AuthError
from atlas.application.container import Container
from atlas.domain.models.user import TokenPair, User
from atlas.infrastructure.config import Settings
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus
from atlas.presentation.api.main import create_app


@pytest.fixture
def app():
    settings = Settings(
        jwt_secret="test-secret-key-for-pytest-only-32chars",
        log_json=False,
        database_url="postgresql+asyncpg://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379/0",
        market_data_mock_enabled=False,
        auth_enabled=True,
    )
    application = create_app(settings)

    now = datetime.now(UTC)
    user = User(
        id=uuid4(),
        email="trader@example.com",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    tokens = TokenPair(
        access_token="access-token",
        refresh_token="refresh-token",
        token_type="bearer",
        expires_in=1800,
    )

    auth_service = MagicMock()
    auth_service.register = AsyncMock(return_value=user)
    auth_service.login = AsyncMock(return_value=(user, tokens))
    auth_service.refresh = AsyncMock(return_value=tokens)
    auth_service.get_user = AsyncMock(return_value=user)
    auth_service.verify_access_token = MagicMock(return_value=user.id)

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
        decision_engine=MagicMock(),
        journal_service=MagicMock(),
        backtest_runner=MagicMock(),
        analytics_service=MagicMock(),
        risk_management_service=MagicMock(),
        execution_service=MagicMock(),
        position_management_service=MagicMock(),
        ai_explanation_service=MagicMock(),
        auth_service=auth_service,
    )
    application.state.ws_manager = MagicMock()
    return application


@pytest.mark.asyncio
async def test_login_returns_tokens(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "trader@example.com", "password": "password123"},
        )
    assert response.status_code == 200
    assert response.json()["data"]["access_token"] == "access-token"


@pytest.mark.asyncio
async def test_me_requires_bearer_token(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_profile_with_token(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer access-token"},
        )
    assert response.status_code == 200
    assert response.json()["data"]["email"] == "trader@example.com"


@pytest.mark.asyncio
async def test_auth_disabled_returns_503() -> None:
    settings = Settings(
        jwt_secret="test-secret-key-for-pytest-only-32chars",
        log_json=False,
        database_url="postgresql+asyncpg://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379/0",
        market_data_mock_enabled=False,
        auth_enabled=False,
    )
    application = create_app(settings)
    application.state.container = MagicMock()
    application.state.container.auth_service = MagicMock()
    application.state.ws_manager = MagicMock()

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "trader@example.com", "password": "password123"},
        )
    assert response.status_code == 503
