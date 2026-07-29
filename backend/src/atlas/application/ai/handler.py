"""Optional background AI explanation on decision.emitted."""

import asyncio

import structlog

from atlas.application.container import Container
from atlas.domain.events.base import DomainEvent
from atlas.infrastructure.config import Settings

logger = structlog.get_logger(__name__)


def make_ai_explanation_handler(container: Container, settings: Settings):
    """Return sync handler that schedules non-blocking explanation generation."""

    def handler(event: DomainEvent) -> None:
        if not settings.ai_explanation_enabled or not settings.ai_explanation_auto:
            return
        snapshot = event.payload.get("decision_snapshot")
        if not snapshot or not snapshot.get("id"):
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_explain(container, snapshot["id"]))
        except RuntimeError:
            logger.warning("ai_explanation_skipped_no_loop")

    return handler


async def _explain(container: Container, decision_id: str) -> None:
    from uuid import UUID

    try:
        await container.ai_explanation_service.explain(UUID(decision_id))
    except Exception:
        logger.exception("ai_explanation_background_failed", decision_id=decision_id)
