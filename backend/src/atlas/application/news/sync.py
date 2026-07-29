"""Background news calendar sync and window monitoring."""

import asyncio

import structlog

from atlas.application.container import Container
from atlas.infrastructure.config import Settings

logger = structlog.get_logger(__name__)


async def run_news_calendar_sync(container: Container, settings: Settings) -> None:
    """Periodically refresh calendar and emit window transition events."""
    sync_seconds = settings.news_calendar_sync_interval_minutes * 60
    monitor_seconds = 60

    try:
        await container.news_filter.load_events()
        if not container.news_filter._events:
            await container.news_filter.refresh_calendar()
    except Exception:
        logger.exception("news_calendar_initial_sync_failed")

    last_sync = asyncio.get_event_loop().time()

    while True:
        try:
            now_mono = asyncio.get_event_loop().time()
            if now_mono - last_sync >= sync_seconds:
                await container.news_filter.refresh_calendar()
                last_sync = now_mono

            container.news_filter.emit_window_transitions()
        except Exception:
            logger.exception("news_calendar_sync_loop_failed")

        await asyncio.sleep(monitor_seconds)
