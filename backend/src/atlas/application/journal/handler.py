"""Journal event handlers."""

import asyncio

import structlog

from atlas.application.container import Container
from atlas.domain.events.base import DomainEvent
from atlas.infrastructure.cache.decision_cache import decision_from_cache_dict

logger = structlog.get_logger(__name__)


def make_journal_decision_handler(container: Container):
    """Return sync handler that records decisions from decision.emitted."""

    def handler(event: DomainEvent) -> None:
        snapshot = event.payload.get("decision_snapshot")
        if not snapshot:
            logger.warning(
                "journal_decision_skipped_no_snapshot",
                correlation_id=event.correlation_id,
            )
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_record_decision(container, snapshot))
        except RuntimeError:
            logger.warning("journal_decision_skipped_no_loop", correlation_id=event.correlation_id)

    return handler


async def _record_decision(container: Container, snapshot: dict) -> None:
    try:
        decision = decision_from_cache_dict(snapshot)
        await container.journal_service.on_decision(decision)
    except Exception:
        logger.exception("journal_decision_record_failed", decision_id=snapshot.get("id"))
