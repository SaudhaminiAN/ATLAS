"""Journal trade lifecycle event handlers (Spec 13 Phase 3)."""

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import structlog

from atlas.application.container import Container
from atlas.domain.events.base import DomainEvent
from atlas.domain.models.journal import TradeLifecycleEvent

logger = structlog.get_logger(__name__)

TRADE_JOURNAL_EVENT_TYPES = frozenset(
    {
        "trade.opened",
        "trade.rejected",
        "trade.sl_moved",
        "trade.partial_closed",
        "trade.closed",
    }
)


def make_journal_trade_handler(container: Container):
    """Return sync handler that records trade lifecycle events in the journal."""

    def handler(event: DomainEvent) -> None:
        if event.event_type not in TRADE_JOURNAL_EVENT_TYPES:
            return
        trade_id_raw = event.payload.get("trade_id")
        if not trade_id_raw:
            logger.warning("journal_trade_skipped_no_trade_id", event_type=event.event_type)
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_record_trade_event(container, event, UUID(str(trade_id_raw))))
        except RuntimeError:
            logger.warning("journal_trade_skipped_no_loop", event_type=event.event_type)

    return handler


async def _record_trade_event(
    container: Container, event: DomainEvent, trade_id: UUID
) -> None:
    try:
        lifecycle = TradeLifecycleEvent(
            trade_id=trade_id,
            event_type=event.event_type,
            payload=event.payload,
            correlation_id=event.correlation_id,
            occurred_at=event.occurred_at or datetime.now(UTC),
        )
        await container.journal_service.on_trade_event(lifecycle)
    except Exception:
        logger.exception("journal_trade_event_failed", trade_id=str(trade_id))
