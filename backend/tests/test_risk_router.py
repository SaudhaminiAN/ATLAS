"""Risk API endpoint tests."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from atlas.application.container import Container
from atlas.domain.models.risk import RiskProfile
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
    profile = RiskProfile(
        id="default",
        account_balance=Decimal("10000"),
        max_risk_percent=Decimal("1.0"),
        max_daily_loss_percent=Decimal("3.0"),
        max_open_positions=2,
        min_rr=Decimal("2.0"),
        buffer_atr_multiplier=Decimal("0.2"),
        max_sl_distance_atr=Decimal("3.0"),
        min_sl_pips=5,
        min_lot=Decimal("0.01"),
        lot_step=Decimal("0.01"),
        updated_at=datetime.now(UTC),
    )
    risk_service = MagicMock()
    risk_service.get_profile = AsyncMock(return_value=profile)
    risk_service.update_profile = AsyncMock(return_value=profile)

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
        risk_management_service=risk_service,
        execution_service=MagicMock(),
        position_management_service=MagicMock(),
        ai_explanation_service=MagicMock(),
    )
    return application


@pytest.mark.asyncio
async def test_get_risk_profile(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/risk/profile")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["account_balance"] == "10000"
