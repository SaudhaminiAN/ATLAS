"""Journal trade handler tests."""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from atlas.application.journal.trade_handler import make_journal_trade_handler
from atlas.domain.events.base import DomainEvent


@pytest.mark.asyncio
async def test_trade_handler_records_lifecycle_event() -> None:
    trade_id = uuid4()
    journal_service = MagicMock()
    journal_service.on_trade_event = AsyncMock()
    container = MagicMock()
    container.journal_service = journal_service

    handler = make_journal_trade_handler(container)
    handler(
        DomainEvent(
            event_type="trade.closed",
            correlation_id="corr-1",
            payload={"trade_id": str(trade_id), "symbol": "XAUUSD"},
        )
    )
    await asyncio.sleep(0)
    journal_service.on_trade_event.assert_awaited_once()
    call_arg = journal_service.on_trade_event.await_args[0][0]
    assert call_arg.trade_id == trade_id
    assert call_arg.event_type == "trade.closed"


@pytest.mark.asyncio
async def test_trade_handler_ignores_unknown_events() -> None:
    journal_service = MagicMock()
    journal_service.on_trade_event = AsyncMock()
    container = MagicMock()
    container.journal_service = journal_service

    handler = make_journal_trade_handler(container)
    handler(
        DomainEvent(
            event_type="decision.emitted",
            correlation_id="corr-1",
            payload={"trade_id": str(uuid4())},
        )
    )
    await asyncio.sleep(0)
    journal_service.on_trade_event.assert_not_awaited()
