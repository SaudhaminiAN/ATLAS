"""Instrument endpoints."""

from fastapi import APIRouter, Request

from atlas.presentation.api.dtos.market_data import InstrumentDTO
from atlas.presentation.api.schemas import ApiEnvelope

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.get("")
async def list_instruments(request: Request) -> ApiEnvelope[list[InstrumentDTO]]:
    """List supported instruments."""
    service = request.app.state.container.market_data_service
    instruments = await service.list_instruments()
    data = [
        InstrumentDTO(
            symbol=i.symbol,
            display_name=i.display_name,
            pip_size=i.pip_size,
            lot_size=i.lot_size,
            is_active=i.is_active,
        )
        for i in instruments
    ]
    return ApiEnvelope(success=True, data=data)
