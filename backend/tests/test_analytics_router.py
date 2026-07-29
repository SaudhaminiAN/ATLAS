"""Analytics API endpoint tests."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from atlas.application.container import Container
from atlas.domain.models.analytics import (
    DecisionStats,
    ModuleAccuracy,
    PerformanceSummary,
    WaitReasonCount,
)
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
    analytics_service = MagicMock()
    analytics_service.get_decision_stats = AsyncMock(
        return_value=DecisionStats(
            total_decisions=10,
            wait_count=8,
            buy_count=1,
            sell_count=1,
            actionable_count=2,
            wait_rate=Decimal("0.8"),
            actionable_rate=Decimal("0.2"),
            top_wait_reasons=(
                WaitReasonCount(reason="Validation failed: direction_check", count=8),
            ),
        )
    )
    analytics_service.get_module_accuracy = AsyncMock(
        return_value=[
            ModuleAccuracy(
                source="mtf_alignment",
                appearances=10,
                true_positive=0,
                false_signal=0,
                neutral_wait=10,
                true_positive_rate=Decimal("0"),
                false_signal_rate=Decimal("0"),
            ),
        ]
    )
    analytics_service.get_performance_summary = AsyncMock(
        return_value=PerformanceSummary(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=Decimal("0"),
            profit_factor=Decimal("0"),
            total_pnl=Decimal("0"),
            max_drawdown=Decimal("0"),
        )
    )
    analytics_service.get_equity_curve = AsyncMock(return_value=[])

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
        analytics_service=analytics_service,
        risk_management_service=MagicMock(),
        execution_service=MagicMock(),
        position_management_service=MagicMock(),
        ai_explanation_service=MagicMock(),
        auth_service=MagicMock(),
    )
    return application


@pytest.mark.asyncio
async def test_decision_stats_endpoint(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/analytics/decision-stats?symbol=XAUUSD")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["total_decisions"] == 10
    assert body["data"]["wait_rate"] == "0.8"


@pytest.mark.asyncio
async def test_module_accuracy_endpoint(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/analytics/module-accuracy")

    assert response.status_code == 200
    body = response.json()
    assert body["data"][0]["source"] == "mtf_alignment"
    assert body["data"][0]["appearances"] == 10


@pytest.mark.asyncio
async def test_performance_endpoint_zeroed_without_trades(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/analytics/performance")

    assert response.status_code == 200
    assert response.json()["data"]["total_trades"] == 0
