"""Trigger analysis pipeline on primary timeframe bar close."""

import asyncio
from datetime import datetime

import structlog

from atlas.application.container import Container
from atlas.domain.models.enums import Timeframe
from atlas.infrastructure.config import Settings

logger = structlog.get_logger(__name__)


def make_pipeline_bar_handler(container: Container, settings: Settings):
    """Return sync handler that schedules pipeline run on bar close."""

    def handler(event) -> None:
        symbol = event.payload.get("symbol")
        timeframe = event.payload.get("timeframe")
        open_time_raw = event.payload.get("open_time")

        if not symbol or timeframe != settings.market_context_primary_timeframe:
            return

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                _run_pipeline(
                    container,
                    symbol,
                    open_time_raw,
                    event.correlation_id,
                    settings.market_context_primary_timeframe,
                )
            )
        except RuntimeError:
            logger.warning("pipeline_run_skipped_no_loop", symbol=symbol)

    return handler


async def _run_pipeline(
    container: Container,
    symbol: str,
    open_time_raw: str | None,
    correlation_id: str | None,
    primary_timeframe: str,
) -> None:
    try:
        instrument = await container.market_data_service.get_instrument(symbol)
        if not instrument:
            return

        as_of = datetime.fromisoformat(open_time_raw) if open_time_raw else None
        bars = await container.market_data_service.get_recent_bars(
            instrument,
            Timeframe(primary_timeframe),
            limit=1,
            as_of=as_of,
        )
        if not bars:
            logger.warning("pipeline_no_trigger_bar", symbol=symbol)
            return

        trigger_bar = bars[-1]
        await container.pipeline.run(
            instrument,
            trigger_bar,
            correlation_id=correlation_id,
        )
    except Exception:
        logger.exception("pipeline_run_failed", symbol=symbol)
