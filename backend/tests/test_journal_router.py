"""Journal REST endpoint tests."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from atlas.application.container import Container
from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.enums import Direction
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.journal import PaginatedResult
from atlas.infrastructure.config import Settings
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus
from atlas.presentation.api.main import create_app


@pytest.fixture
def app():
    """FastAPI app with mocked journal service."""
    settings = Settings(
        jwt_secret="test-secret-key-for-pytest-only-32chars",
        log_json=False,
        database_url="postgresql+asyncpg://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379/0",
        market_data_mock_enabled=False,
    )
    application = create_app(settings)

    instrument = Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )
    decision = TradingDecision(
        id=uuid4(),
        instrument=instrument,
        direction=Direction.WAIT,
        is_actionable=False,
        confluence_score=Decimal("0.55"),
        strategy_id="test",
        reason="Confluence below threshold",
        correlation_id="corr-abc",
        decided_at=datetime.now(UTC),
    )

    journal_service = MagicMock()
    journal_service.query_decisions = AsyncMock(
        return_value=PaginatedResult(
            items=(decision,),
            total=1,
            limit=50,
            offset=0,
        )
    )

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
        journal_service=journal_service,
        backtest_runner=MagicMock(),
        analytics_service=MagicMock(),
        risk_management_service=MagicMock(),
        execution_service=MagicMock(),
        position_management_service=MagicMock(),
        ai_explanation_service=MagicMock(),
    )
    application.state.ws_manager = MagicMock()
    return application


@pytest.mark.asyncio
async def test_query_journal_decisions(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/journal/decisions",
            params={
                "symbol": "XAUUSD",
                "direction": "WAIT",
                "correlation_id": "corr-abc",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["direction"] == "WAIT"
    assert body["data"]["items"][0]["correlation_id"] == "corr-abc"

    app.state.container.journal_service.query_decisions.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_trade_journal_endpoint(app) -> None:
    from atlas.domain.models.journal import TradeJournalView

    trade_id = uuid4()
    app.state.container.journal_service.get_trade_journal = AsyncMock(
        return_value=TradeJournalView(
            trade_id=trade_id,
            decision_id=uuid4(),
            symbol="XAUUSD",
            direction="BUY",
            status="open",
            events=(),
            notes=(),
        )
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/journal/trades/{trade_id}")

    assert response.status_code == 200
    assert response.json()["data"]["symbol"] == "XAUUSD"


@pytest.mark.asyncio
async def test_add_trade_note_endpoint(app) -> None:
    from atlas.domain.models.journal import JournalEntry

    trade_id = uuid4()
    app.state.container.journal_service.add_note = AsyncMock(
        return_value=JournalEntry(
            id=uuid4(),
            decision_id=uuid4(),
            trade_id=trade_id,
            user_id=uuid4(),
            entry_type="note",
            content="Strong setup",
            tags=("smc",),
            created_at=datetime.now(UTC),
        )
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/journal/trades/{trade_id}/notes",
            json={"content": "Strong setup", "tags": ["smc"]},
        )

    assert response.status_code == 200
    assert response.json()["data"]["content"] == "Strong setup"
