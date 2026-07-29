"""Journal service tests."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from atlas.application.journal.service import JournalService
from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.enums import Direction
from atlas.domain.models.execution import Trade, TradeEvent, TradeStatus
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.journal import DecisionFilters, JournalEntry, PaginatedResult, TradeLifecycleEvent


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


def _trade() -> Trade:
    now = datetime.now(UTC)
    return Trade(
        id=uuid4(),
        decision_id=uuid4(),
        instrument=_instrument(),
        direction=Direction.BUY,
        status=TradeStatus.OPEN,
        entry_price=Decimal("2350"),
        fill_price=Decimal("2350.5"),
        stop_loss=Decimal("2340"),
        take_profit=Decimal("2370"),
        position_size=Decimal("0.10"),
        execution_mode="paper",
        rejection_reason=None,
        opened_at=now,
        closed_at=None,
        realized_pnl=None,
    )


def _service(session_factory: MagicMock) -> JournalService:
    return JournalService(session_factory=session_factory, default_user_id=uuid4())


@pytest.mark.asyncio
async def test_on_decision_inserts_idempotently(monkeypatch) -> None:
    session = MagicMock()
    session_factory = MagicMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    service = _service(session_factory)
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

    service = _service(session_factory)
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


@pytest.mark.asyncio
async def test_on_trade_event_warns_when_trade_missing(monkeypatch) -> None:
    session = MagicMock()
    session_factory = MagicMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    service = _service(session_factory)
    trade_repo = MagicMock()
    trade_repo.get = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "atlas.application.journal.service.TradeRepository",
        lambda _session: trade_repo,
    )

    event = TradeLifecycleEvent(
        trade_id=uuid4(),
        event_type="trade.closed",
        payload={},
        correlation_id="c1",
        occurred_at=datetime.now(UTC),
    )
    await service.on_trade_event(event)
    trade_repo.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_note_raises_when_trade_missing(monkeypatch) -> None:
    session = MagicMock()
    session_factory = MagicMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    service = _service(session_factory)
    trade_repo = MagicMock()
    trade_repo.get = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "atlas.application.journal.service.TradeRepository",
        lambda _session: trade_repo,
    )

    with pytest.raises(ValueError, match="Trade not found"):
        await service.add_note(uuid4(), "My note")


@pytest.mark.asyncio
async def test_get_trade_journal_combines_events_and_notes(monkeypatch) -> None:
    session = MagicMock()
    session_factory = MagicMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    service = _service(session_factory)
    trade = _trade()
    event = TradeEvent(
        id=uuid4(),
        trade_id=trade.id,
        event_type="opened",
        payload={"fill_price": "2350.5"},
        created_at=datetime.now(UTC),
    )
    note = JournalEntry(
        id=uuid4(),
        decision_id=trade.decision_id,
        trade_id=trade.id,
        user_id=uuid4(),
        entry_type="note",
        content="Good entry",
        tags=("setup",),
        created_at=datetime.now(UTC),
    )

    trade_repo = MagicMock()
    trade_repo.get = AsyncMock(return_value=trade)
    trade_repo.list_events = AsyncMock(return_value=[event])
    journal_repo = MagicMock()
    journal_repo.list_by_trade = AsyncMock(return_value=[note])
    monkeypatch.setattr(
        "atlas.application.journal.service.TradeRepository",
        lambda _session: trade_repo,
    )
    monkeypatch.setattr(
        "atlas.application.journal.service.JournalRepository",
        lambda _session: journal_repo,
    )

    view = await service.get_trade_journal(trade.id)
    assert view.trade_id == trade.id
    assert len(view.events) == 1
    assert len(view.notes) == 1
    assert view.notes[0].content == "Good entry"
