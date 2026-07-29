"""Execution service tests."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from atlas.application.execution.service import ExecutionService
from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.enums import Direction
from atlas.domain.models.execution import OrderResult, OrderStatus
from atlas.domain.models.instrument import Instrument
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def _actionable_decision() -> TradingDecision:
    return TradingDecision(
        id=uuid4(),
        instrument=_instrument(),
        direction=Direction.BUY,
        is_actionable=True,
        confluence_score=Decimal("0.8"),
        strategy_id="test",
        reason="ok",
        correlation_id="cid",
        decided_at=datetime.now(UTC),
        risk_snapshot={
            "within_limits": True,
            "parameters": {
                "entry_price": "2350",
                "stop_loss": "2340",
                "take_profit": "2370",
                "position_size": "0.10",
                "risk_amount": "100",
                "reward_risk_ratio": "2.0",
                "sl_basis": "support",
            },
        },
    )


@pytest.mark.asyncio
async def test_skips_non_actionable() -> None:
    service = ExecutionService(
        session_factory=MagicMock(),
        provider=MagicMock(),
        idempotency_cache=MagicMock(),
        event_bus=InMemoryEventBus(),
    )
    decision = _actionable_decision()
    wait = TradingDecision(
        id=decision.id,
        instrument=decision.instrument,
        direction=Direction.WAIT,
        is_actionable=False,
        confluence_score=Decimal("0"),
        strategy_id="test",
        reason="wait",
        correlation_id="cid",
        decided_at=decision.decided_at,
    )
    result = await service.on_decision(wait)
    assert result is None


@pytest.mark.asyncio
async def test_rejects_without_risk_snapshot() -> None:
    bus = InMemoryEventBus()
    events: list[str] = []
    bus.subscribe("trade.rejected", lambda e: events.append(e.event_type))

    session = MagicMock()
    session_factory = MagicMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = MagicMock()
    repo.get_by_decision_id = AsyncMock(return_value=None)
    repo.insert = AsyncMock(return_value=True)
    repo.append_event = AsyncMock()

    idempotency = MagicMock()
    idempotency.try_acquire = AsyncMock(return_value=True)

    service = ExecutionService(
        session_factory=session_factory,
        provider=MagicMock(),
        idempotency_cache=idempotency,
        event_bus=bus,
    )

    decision = _actionable_decision()
    decision = TradingDecision(
        id=decision.id,
        instrument=decision.instrument,
        direction=decision.direction,
        is_actionable=True,
        confluence_score=decision.confluence_score,
        strategy_id=decision.strategy_id,
        reason=decision.reason,
        correlation_id=decision.correlation_id,
        decided_at=decision.decided_at,
        risk_snapshot=None,
    )

    with patch("atlas.application.execution.service.TradeRepository") as repo_cls:
        repo_cls.return_value = repo
        result = await service.on_decision(decision)

    assert result is not None
    assert result.status == OrderStatus.REJECTED
    assert events == ["trade.rejected"]
