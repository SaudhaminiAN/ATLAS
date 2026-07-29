"""News API endpoint tests."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from atlas.application.container import Container
from atlas.domain.models.news import NewsFilterStatus
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
        news_mock_enabled=False,
    )
    application = create_app(settings)
    news_filter = MagicMock()
    news_filter.get_upcoming = AsyncMock(return_value=[])
    news_filter.check = MagicMock(
        return_value=NewsFilterStatus(
            is_blocked=False,
            is_soft_downgrade=False,
            confluence_penalty=Decimal("0"),
            next_event=None,
            as_of=datetime.now(UTC),
        )
    )

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
        news_filter=news_filter,
        market_context_service=MagicMock(),
        mtf_service=MagicMock(),
        technical_analysis_service=MagicMock(),
        smc_service=MagicMock(),
    )
    application.state.ws_manager = MagicMock()
    return application


@pytest.mark.asyncio
async def test_news_status_endpoint(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/news/status")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["is_blocked"] is False


@pytest.mark.asyncio
async def test_news_upcoming_endpoint(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/news/upcoming")

    assert response.status_code == 200
    assert response.json()["success"] is True
