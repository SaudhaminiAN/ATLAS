"""Integration-style journal lifecycle tests (Spec 13 Phase 3)."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from atlas.application.journal.service import JournalService
from atlas.domain.models.enums import Direction
from atlas.domain.models.execution import Trade, TradeEvent, TradeStatus
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.journal import TradeLifecycleEvent


def _trade(status: TradeStatus = TradeStatus.OPEN) -> Trade:
    now = datetime.now(UTC)
    instrument = Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )
    return Trade(
        id=uuid4(),
        decision_id=uuid4(),
        instrument=instrument,
        direction=Direction.BUY,
        status=status,
        entry_price=Decimal("2350"),
        fill_price=Decimal("2350.5"),
        stop_loss=Decimal("2340"),
        take_profit=Decimal("2370"),
        position_size=Decimal("0.10"),
        execution_mode="paper",
        rejection_reason=None,
        opened_at=now,
        closed_at=now if status == TradeStatus.CLOSED else None,
        realized_pnl=Decimal("2.5") if status == TradeStatus.CLOSED else None,
    )


@pytest.mark.asyncio
async def test_full_lifecycle_open_sl_close_with_note(monkeypatch) -> None:
    """open → sl_moved → closed with trader note."""
    session = MagicMock()
    session_factory = MagicMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    user_id = uuid4()
    service = JournalService(session_factory=session_factory, default_user_id=user_id)
    trade = _trade()

    events: list[TradeEvent] = [
        TradeEvent(
            id=uuid4(),
            trade_id=trade.id,
            event_type="opened",
            payload={"fill_price": "2350.5"},
            created_at=datetime.now(UTC),
        ),
        TradeEvent(
            id=uuid4(),
            trade_id=trade.id,
            event_type="sl_moved",
            payload={"reason": "breakeven", "new_sl": "2350"},
            created_at=datetime.now(UTC),
        ),
    ]
    closed_trade = _trade(TradeStatus.CLOSED)
    closed_trade = Trade(
        id=trade.id,
        decision_id=trade.decision_id,
        instrument=trade.instrument,
        direction=trade.direction,
        status=TradeStatus.CLOSED,
        entry_price=trade.entry_price,
        fill_price=trade.fill_price,
        stop_loss=Decimal("2350"),
        take_profit=trade.take_profit,
        position_size=trade.position_size,
        execution_mode=trade.execution_mode,
        rejection_reason=None,
        opened_at=trade.opened_at,
        closed_at=datetime.now(UTC),
        realized_pnl=Decimal("1.0"),
    )
    events.append(
        TradeEvent(
            id=uuid4(),
            trade_id=trade.id,
            event_type="closed",
            payload={"reason": "sl_hit", "total_realized_pnl": "1.0"},
            created_at=datetime.now(UTC),
        )
    )

    trade_repo = MagicMock()
    trade_repo.get = AsyncMock(side_effect=[trade, trade, trade, trade, closed_trade])
    trade_repo.list_events = AsyncMock(return_value=events)

    journal_repo = MagicMock()
    stored_note = None

    async def _insert_note(**kwargs):
        nonlocal stored_note
        from atlas.domain.models.journal import JournalEntry

        stored_note = JournalEntry(
            id=uuid4(),
            decision_id=kwargs.get("decision_id"),
            trade_id=kwargs["trade_id"],
            user_id=kwargs["user_id"],
            entry_type="note",
            content=kwargs["content"],
            tags=tuple(kwargs["tags"]),
            created_at=datetime.now(UTC),
        )
        return stored_note

    journal_repo.insert_note = AsyncMock(side_effect=_insert_note)
    journal_repo.list_by_trade = AsyncMock(
        side_effect=lambda _tid: [stored_note] if stored_note else []
    )

    monkeypatch.setattr(
        "atlas.application.journal.service.TradeRepository",
        lambda _session: trade_repo,
    )
    monkeypatch.setattr(
        "atlas.application.journal.service.JournalRepository",
        lambda _session: journal_repo,
    )

    await service.on_trade_event(
        TradeLifecycleEvent(
            trade_id=trade.id,
            event_type="trade.opened",
            payload={"trade_id": str(trade.id)},
            correlation_id="c1",
            occurred_at=datetime.now(UTC),
        )
    )
    await service.on_trade_event(
        TradeLifecycleEvent(
            trade_id=trade.id,
            event_type="trade.sl_moved",
            payload={"reason": "breakeven"},
            correlation_id="c2",
            occurred_at=datetime.now(UTC),
        )
    )
    await service.add_note(trade.id, "Moved to breakeven as planned", ["breakeven"])
    await service.on_trade_event(
        TradeLifecycleEvent(
            trade_id=trade.id,
            event_type="trade.closed",
            payload={"reason": "sl_hit"},
            correlation_id="c3",
            occurred_at=datetime.now(UTC),
        )
    )

    view = await service.get_trade_journal(trade.id)
    assert view.status == "closed"
    assert len(view.events) == 3
    assert len(view.notes) == 1
    assert view.notes[0].content == "Moved to breakeven as planned"
