"""Position management bar event handler."""

import asyncio

import structlog

from atlas.application.container import Container
from atlas.domain.events.base import DomainEvent
from atlas.infrastructure.config import Settings

logger = structlog.get_logger(__name__)


def make_position_management_bar_handler(container: Container, settings: Settings):
    """Return sync handler that monitors open positions on bar close."""

    def handler(event: DomainEvent) -> None:
        if not settings.position_management_enabled or not settings.execution_enabled:
            return
        symbol = event.payload.get("symbol")
        timeframe = event.payload.get("timeframe")
        if not symbol or not timeframe:
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_on_bar(container, symbol, timeframe))
        except RuntimeError:
            logger.warning("position_mgmt_skipped_no_loop", symbol=symbol)

    return handler


async def _on_bar(container: Container, symbol: str, timeframe: str) -> None:
    try:
        await container.position_management_service.on_bar(symbol, timeframe)
    except Exception:
        logger.exception("position_mgmt_failed", symbol=symbol)
