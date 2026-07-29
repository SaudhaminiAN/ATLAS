"""Recompute market context when new bars arrive."""

import asyncio

import structlog

from atlas.application.container import Container
from atlas.domain.events.base import DomainEvent
from atlas.infrastructure.config import Settings

logger = structlog.get_logger(__name__)


def make_bar_context_handler(container: Container, settings: Settings):
    """Return sync handler that schedules async context update."""

    def handler(event: DomainEvent) -> None:
        symbol = event.payload.get("symbol")
        timeframe = event.payload.get("timeframe")
        if not symbol or timeframe != settings.market_context_primary_timeframe:
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_update_context(container, symbol))
        except RuntimeError:
            logger.warning("market_context_update_skipped_no_loop", symbol=symbol)

    return handler


async def _update_context(container: Container, symbol: str) -> None:
    try:
        await container.market_context_service.analyze_symbol(symbol)
    except Exception:
        logger.exception("market_context_update_failed", symbol=symbol)
