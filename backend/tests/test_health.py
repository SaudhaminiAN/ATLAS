"""API health endpoint tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from atlas.application.container import Container
from atlas.infrastructure.config import Settings
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus
from atlas.presentation.api.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    """Settings for tests."""
    return Settings(
        jwt_secret="test-secret-key-for-pytest-only-32chars",
        log_json=False,
        database_url="postgresql+asyncpg://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379/0",
        market_data_mock_enabled=False,
    )


@pytest.fixture
def app(test_settings: Settings):
    """FastAPI app with mocked container."""
    application = create_app(test_settings)
    mock_engine = MagicMock()
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)

    container = Container(
        settings=test_settings,
        event_bus=InMemoryEventBus(),
        engine=mock_engine,
        session_factory=MagicMock(),
        redis=mock_redis,
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
    )
    application.state.container = container
    application.state.ws_manager = MagicMock()
    return application


@pytest.mark.asyncio
async def test_health_returns_200(app) -> None:
    """Liveness endpoint returns success envelope."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"


@pytest.mark.asyncio
async def test_ready_returns_200_when_dependencies_ok(app, monkeypatch) -> None:
    """Readiness returns 200 when DB and Redis are reachable."""
    monkeypatch.setattr(
        "atlas.presentation.api.routers.health.check_database",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        "atlas.presentation.api.routers.health.check_redis",
        AsyncMock(return_value=True),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json()["data"]["database"] == "ok"


@pytest.mark.asyncio
async def test_ready_returns_503_when_database_down(app, monkeypatch) -> None:
    """Readiness returns 503 when database is unavailable."""
    monkeypatch.setattr(
        "atlas.presentation.api.routers.health.check_database",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        "atlas.presentation.api.routers.health.check_redis",
        AsyncMock(return_value=True),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json()["success"] is False
