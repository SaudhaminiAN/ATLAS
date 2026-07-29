"""Journal service tests."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from atlas.application.journal.service import JournalService
from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.enums import Direction
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.journal import DecisionFilters, PaginatedResult


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def _decision(direction: Direction = Direction.WAIT) -> TradingDecision:
    return TradingDecision(
        id=uuid4(),
        instrument=_instrument(),
        direction=direction,
        is_actionable=direction != Direction.WAIT,
        confluence_score=Decimal("0.55"),
        strategy_id="test",
        reason="Test reason",
        correlation_id="corr-1",
        decided_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_on_decision_inserts_idempotently(monkeypatch) -> None:
    session = MagicMock()
    session_factory = MagicMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    service = JournalService(session_factory=session_factory)
    decision = _decision()

    repo = MagicMock()
    repo.insert_idempotent = AsyncMock(side_effect=[True, False])
    monkeypatch.setattr(
        "atlas.application.journal.service.DecisionRepository",
        lambda _session: repo,
    )
    await service.on_decision(decision)
    await service.on_decision(decision)

    assert repo.insert_idempotent.await_count == 2


@pytest.mark.asyncio
async def test_query_decisions_returns_paginated_result(monkeypatch) -> None:
    session = MagicMock()
    session_factory = MagicMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    service = JournalService(session_factory=session_factory)
    decision = _decision(Direction.BUY)
    filters = DecisionFilters(symbol="XAUUSD", limit=10, offset=0)

    repo = MagicMock()
    repo.query = AsyncMock(return_value=[decision])
    repo.count = AsyncMock(return_value=1)
    monkeypatch.setattr(
        "atlas.application.journal.service.DecisionRepository",
        lambda _session: repo,
    )
    result = await service.query_decisions(filters)

    assert isinstance(result, PaginatedResult)
    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0].direction == Direction.BUY
