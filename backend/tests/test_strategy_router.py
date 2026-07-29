"""Strategy API endpoint tests."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from atlas.application.container import Container
from atlas.application.strategy.service import ProfileValidationError
from atlas.domain.models.enums import Direction, Timeframe, TradingSession
from atlas.domain.models.strategy import StrategyProfile
from atlas.infrastructure.config import Settings
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus
from atlas.presentation.api.main import create_app


def _sample_profile(*, profile_id: str = "xauusd_conservative", is_active: bool = True):
    return StrategyProfile(
        id=profile_id,
        name="XAUUSD Conservative",
        min_confluence_score=Decimal("0.70"),
        enabled_directions=(Direction.BUY, Direction.SELL),
        confluence_weights={"mtf_alignment": Decimal("0.25")},
        active_timeframes=(Timeframe.D1, Timeframe.H4),
        allowed_sessions=(TradingSession.LONDON,),
        validation_rule_flags={"session_check": True},
        is_active=is_active,
        updated_at=datetime.now(UTC),
    )


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
    strategy_engine = MagicMock()
    strategy_engine.list_profiles = AsyncMock(return_value=[_sample_profile()])
    strategy_engine.get_active = AsyncMock(return_value=_sample_profile())
    strategy_engine.set_active = AsyncMock(return_value=_sample_profile())

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
        strategy_engine=strategy_engine,
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
    )
    application.state.ws_manager = MagicMock()
    return application


@pytest.mark.asyncio
async def test_list_strategy_profiles(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/strategy/profiles")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"][0]["id"] == "xauusd_conservative"
    assert body["data"][0]["validation_rules"]["session_check"] is True


@pytest.mark.asyncio
async def test_get_active_strategy_profile(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/strategy/active")

    assert response.status_code == 200
    assert response.json()["data"]["is_active"] is True


@pytest.mark.asyncio
async def test_put_active_strategy_profile(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/api/v1/strategy/active",
            json={"profile_id": "xauusd_conservative"},
        )

    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_put_active_invalid_profile_returns_validation_error(app) -> None:
    app.state.container.strategy_engine.set_active = AsyncMock(
        side_effect=ProfileValidationError(["min_confluence_score must be between 0.0 and 1.0"])
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/api/v1/strategy/active",
            json={"profile_id": "bad_profile"},
        )

    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
