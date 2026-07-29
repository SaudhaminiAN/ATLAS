"""Market data REST endpoints."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request

from atlas.domain.models.enums import Timeframe
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.presentation.api.dtos.market_data import OHLCVBarDTO
from atlas.presentation.api.schemas import ApiEnvelope, ApiError

router = APIRouter(prefix="/market-data", tags=["market-data"])


def _to_dto(bar: OHLCVBar) -> OHLCVBarDTO:
    return OHLCVBarDTO(
        symbol=bar.instrument.symbol,
        timeframe=bar.timeframe.value,
        open_time=bar.open_time,
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        volume=bar.volume,
        is_outlier=bar.is_outlier,
        quality_flags=bar.quality_flags,
    )


@router.get("/{symbol}/bars")
async def get_bars(
    request: Request,
    symbol: str,
    timeframe: Timeframe = Query(default=Timeframe.M15),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    limit: int = Query(default=500, le=1000),
) -> ApiEnvelope[list[OHLCVBarDTO]]:
    """Historical OHLCV bars."""
    service = request.app.state.container.market_data_service
    instrument = await service.get_instrument(symbol)
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")

    from datetime import UTC, timedelta

    end_dt = end or datetime.now(UTC)
    start_dt = start or (end_dt - timedelta(days=7))

    bars = await service.get_history(instrument, timeframe, start_dt, end_dt, limit)
    return ApiEnvelope(success=True, data=[_to_dto(b) for b in bars])


@router.get("/{symbol}/latest")
async def get_latest_bar(
    request: Request,
    symbol: str,
    timeframe: Timeframe = Query(default=Timeframe.M15),
) -> ApiEnvelope[OHLCVBarDTO]:
    """Latest OHLCV bar for symbol/timeframe."""
    service = request.app.state.container.market_data_service
    instrument = await service.get_instrument(symbol)
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")

    bar = await service.get_latest(instrument, timeframe)
    if not bar:
        return ApiEnvelope(
            success=False,
            data=None,
            error=ApiError(code="NOT_FOUND", message="No bars available"),
        )
    return ApiEnvelope(success=True, data=_to_dto(bar))
