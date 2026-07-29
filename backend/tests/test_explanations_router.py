"""AI explanation REST endpoint tests."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from atlas.application.ai.service import DecisionNotFoundError, ExplanationRateLimitError
from atlas.application.container import Container
from atlas.domain.models.explanation import DecisionExplanation
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
    )
    application = create_app(settings)
    ai_service = MagicMock()
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
        ai_explanation_service=ai_service,
    )
    application.state.ws_manager = MagicMock()
    ai_service.enabled = True
    return application


@pytest.mark.asyncio
async def test_get_explanation_not_found(app) -> None:
    app.state.container.ai_explanation_service.get_explanation = AsyncMock(return_value=None)
    decision_id = uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/explanations/{decision_id}")
    assert response.status_code == 200
    assert response.json()["success"] is False


@pytest.mark.asyncio
async def test_post_explanation_generates(app) -> None:
    decision_id = uuid4()
    explanation = DecisionExplanation(
        id=uuid4(),
        decision_id=decision_id,
        content="ATLAS issued WAIT on XAUUSD.",
        provider="mock",
        created_at=datetime.now(UTC),
    )
    app.state.container.ai_explanation_service.explain = AsyncMock(return_value=explanation)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/explanations/{decision_id}")

    assert response.status_code == 200
    assert response.json()["data"]["content"].startswith("ATLAS")


@pytest.mark.asyncio
async def test_post_explanation_rate_limited(app) -> None:
    app.state.container.ai_explanation_service.explain = AsyncMock(
        side_effect=ExplanationRateLimitError("limit")
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/explanations/{uuid4()}")
    assert response.status_code == 429


@pytest.mark.asyncio
async def test_post_explanation_decision_not_found(app) -> None:
    app.state.container.ai_explanation_service.explain = AsyncMock(
        side_effect=DecisionNotFoundError("missing")
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/explanations/{uuid4()}")
    assert response.status_code == 404
