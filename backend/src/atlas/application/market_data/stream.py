import asyncio
from datetime import UTC, datetime, timedelta

import structlog

from atlas.application.container import Container
from atlas.domain.models.enums import Timeframe
from atlas.infrastructure.config import Settings
from atlas.infrastructure.persistence.repositories import OHLCVBarRepository

logger = structlog.get_logger(__name__)

BOOTSTRAP_BAR_COUNT = 300


async def _bootstrap_history(container: Container, instrument, timeframe: Timeframe) -> None:
    """Pre-load mock OHLCV history so the chart is readable on first load."""
    async with container.session_factory() as session:
        repo = OHLCVBarRepository(session)
        existing = await repo.count(instrument.id, timeframe)

    if existing >= BOOTSTRAP_BAR_COUNT:
        logger.info(
            "mock_history_skipped",
            symbol=instrument.symbol,
            timeframe=timeframe.value,
            existing=existing,
        )
        return

    if existing > 0:
        async with container.session_factory() as session:
            repo = OHLCVBarRepository(session)
            removed = await repo.delete_for_instrument(instrument.id, timeframe)
        logger.info(
            "mock_history_cleared",
            symbol=instrument.symbol,
            timeframe=timeframe.value,
            removed=removed,
        )

    end = datetime.now(UTC)
    minutes = 15 if timeframe == Timeframe.M15 else 60
    start = end - timedelta(minutes=minutes * BOOTSTRAP_BAR_COUNT)
    bars = await container.mock_provider.fetch_bars(instrument, timeframe, start, end)
    ingested = 0
    for bar in bars:
        result = await container.market_data_service.ingest_bar(bar, is_closed=True)
        if result.status.value == "accepted":
            ingested += 1
    logger.info(
        "mock_history_bootstrapped",
        symbol=instrument.symbol,
        timeframe=timeframe.value,
        generated=len(bars),
        ingested=ingested,
    )


async def run_mock_market_data_stream(container: Container, settings: Settings) -> None:
    """Subscribe to mock provider and ingest closed bars."""
    if not settings.market_data_mock_enabled:
        return

    try:
        timeframe = Timeframe(settings.market_data_mock_timeframe)
    except ValueError:
        logger.error("invalid_mock_timeframe", value=settings.market_data_mock_timeframe)
        return

    instruments = await container.market_data_service.list_instruments()
    if not instruments:
        logger.warning("mock_stream_no_instruments")
        return

    instrument = next((i for i in instruments if i.symbol == "XAUUSD"), instruments[0])
    await _bootstrap_history(container, instrument, timeframe)
    logger.info("mock_stream_started", symbol=instrument.symbol, timeframe=timeframe.value)

    async for bar in container.mock_provider.subscribe_bars(instrument, timeframe):
        try:
            await container.market_data_service.ingest_bar(bar, is_closed=True)
        except Exception:
            logger.exception("mock_stream_ingest_failed")
