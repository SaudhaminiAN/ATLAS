"""Execution event handlers."""

import asyncio

import structlog

from atlas.application.container import Container
from atlas.domain.events.base import DomainEvent
from atlas.infrastructure.cache.decision_cache import decision_from_cache_dict

logger = structlog.get_logger(__name__)


def make_execution_decision_handler(container: Container):
    """Return sync handler that submits paper orders on actionable decisions."""

    def handler(event: DomainEvent) -> None:
        if not event.payload.get("is_actionable"):
            return
        snapshot = event.payload.get("decision_snapshot")
        if not snapshot:
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_execute_decision(container, snapshot))
        except RuntimeError:
            logger.warning("execution_skipped_no_loop", correlation_id=event.correlation_id)

    return handler


async def _execute_decision(container: Container, snapshot: dict) -> None:
    try:
        decision = decision_from_cache_dict(snapshot)
        await container.execution_service.on_decision(decision)
    except Exception:
        logger.exception("execution_decision_failed", decision_id=snapshot.get("id"))
