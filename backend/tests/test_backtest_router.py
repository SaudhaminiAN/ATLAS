"""Backtest API endpoint tests."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from atlas.application.container import Container
from atlas.domain.models.backtest import (
    BacktestResult,
    DecisionSummary,
    ModuleAccuracySummary,
)
from atlas.domain.models.enums import Direction, Timeframe
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
    result = BacktestResult(
        symbol="XAUUSD",
        timeframe=Timeframe.M15,
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 1, 2, tzinfo=UTC),
        bars_processed=10,
        pipeline_runs=10,
        completed_runs=10,
        skipped_runs=0,
        failed_runs=0,
        decision_counts=(DecisionSummary(direction=Direction.WAIT, count=10),),
        wait_reasons=(("Validation failed: direction_check", 10),),
        module_accuracy=(
            ModuleAccuracySummary(
                source="mtf_alignment",
                appearances=10,
                actionable_appearances=0,
            ),
        ),
        duration_ms=500,
    )
    backtest_runner = MagicMock()
    backtest_runner.run = AsyncMock(return_value=result)

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
        backtest_runner=backtest_runner,
        analytics_service=MagicMock(),
        risk_management_service=MagicMock(),
        execution_service=MagicMock(),
        position_management_service=MagicMock(),
        ai_explanation_service=MagicMock(),
        auth_service=MagicMock(),
    )
    return application


@pytest.mark.asyncio
async def test_backtest_run_endpoint(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/backtest/run",
            json={
                "symbol": "XAUUSD",
                "timeframe": "M15",
                "start": "2026-01-01T00:00:00Z",
                "end": "2026-01-02T00:00:00Z",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["bars_processed"] == 10
    assert body["data"]["decision_counts"][0]["direction"] == "WAIT"


@pytest.mark.asyncio
async def test_backtest_run_invalid_range(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/backtest/run",
            json={
                "symbol": "XAUUSD",
                "timeframe": "M15",
                "start": "2026-01-02T00:00:00Z",
                "end": "2026-01-01T00:00:00Z",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "invalid_range"
