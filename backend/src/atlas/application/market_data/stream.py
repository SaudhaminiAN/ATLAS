"""Background mock market data stream."""


import structlog

from atlas.application.container import Container
from atlas.domain.models.enums import Timeframe
from atlas.infrastructure.config import Settings

logger = structlog.get_logger(__name__)


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
    logger.info("mock_stream_started", symbol=instrument.symbol, timeframe=timeframe.value)

    async for bar in container.mock_provider.subscribe_bars(instrument, timeframe):
        try:
            await container.market_data_service.ingest_bar(bar, is_closed=True)
        except Exception:
            logger.exception("mock_stream_ingest_failed")
