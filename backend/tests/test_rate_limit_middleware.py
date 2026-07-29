"""API rate limiting tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from atlas.application.container import Container
from atlas.infrastructure.config import Settings
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus
from atlas.presentation.api.main import create_app


@pytest.fixture
def rate_limit_settings() -> Settings:
    return Settings(
        jwt_secret="test-secret-key-for-pytest-only-32chars",
        log_json=False,
        database_url="postgresql+asyncpg://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379/0",
        market_data_mock_enabled=False,
        rate_limit_enabled=True,
        rate_limit_per_minute=2,
        rate_limit_auth_per_minute=1,
    )


@pytest.fixture
def rate_limit_app(rate_limit_settings: Settings):
    application = create_app(rate_limit_settings)
    redis = AsyncMock()
    redis.incr = AsyncMock(side_effect=[1, 2, 3])
    redis.expire = AsyncMock(return_value=True)
    redis.ttl = AsyncMock(return_value=42)

    decision_engine = MagicMock()
    decision_engine.get_latest = AsyncMock(return_value=None)

    container = Container(
        settings=rate_limit_settings,
        event_bus=InMemoryEventBus(),
        engine=MagicMock(),
        session_factory=MagicMock(),
        redis=redis,
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
        auth_service=MagicMock(),
    )
    application.state.container = container
    application.state.ws_manager = MagicMock()
    return application


@pytest.mark.asyncio
async def test_rate_limit_blocks_after_threshold(rate_limit_app) -> None:
    transport = ASGITransport(app=rate_limit_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.get("/api/v1/decisions/XAUUSD/latest")
        second = await client.get("/api/v1/decisions/XAUUSD/latest")
        third = await client.get("/api/v1/decisions/XAUUSD/latest")

    assert first.status_code != 429
    assert second.status_code != 429
    assert third.status_code == 429
    assert third.json()["error"]["code"] == "RATE_LIMITED"
    assert third.headers.get("Retry-After") == "42"


@pytest.mark.asyncio
async def test_health_exempt_from_rate_limit(rate_limit_app) -> None:
    rate_limit_app.state.container.redis.incr = AsyncMock(return_value=999)

    transport = ASGITransport(app=rate_limit_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_auth_endpoints_use_stricter_limit(rate_limit_app) -> None:
    transport = ASGITransport(app=rate_limit_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post(
            "/api/v1/auth/login",
            json={"email": "a@example.com", "password": "password123"},
        )
        second = await client.post(
            "/api/v1/auth/login",
            json={"email": "a@example.com", "password": "password123"},
        )

    assert first.status_code != 429
    assert second.status_code == 429
