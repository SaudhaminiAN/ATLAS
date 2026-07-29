"""Journal event handler tests."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from atlas.application.journal.handler import make_journal_decision_handler
from atlas.application.journal.service import JournalService
from atlas.domain.events.base import DomainEvent
from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.enums import Direction
from atlas.domain.models.instrument import Instrument
from atlas.infrastructure.cache.decision_cache import decision_from_cache_dict
from atlas.infrastructure.persistence.decision_serializers import decision_to_cache_dict


def _decision() -> TradingDecision:
    instrument = Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )
    return TradingDecision(
        id=uuid4(),
        instrument=instrument,
        direction=Direction.WAIT,
        is_actionable=False,
        confluence_score=Decimal("0.40"),
        strategy_id="test",
        reason="Insufficient evidence",
        correlation_id="corr-99",
        decided_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_handler_records_decision_from_snapshot() -> None:
    decision = _decision()
    snapshot = decision_to_cache_dict(decision)
    rebuilt = decision_from_cache_dict(snapshot)
    assert rebuilt.direction == decision.direction
    assert rebuilt.correlation_id == decision.correlation_id

    journal_service = MagicMock(spec=JournalService)
    journal_service.on_decision = AsyncMock()
    container = MagicMock()
    container.journal_service = journal_service

    handler = make_journal_decision_handler(container)
    handler(
        DomainEvent(
            event_type="decision.emitted",
            correlation_id="corr-99",
            payload={"decision_snapshot": snapshot},
        )
    )

    # Handler schedules async task; give event loop a tick
    import asyncio

    await asyncio.sleep(0)
    journal_service.on_decision.assert_awaited_once()
