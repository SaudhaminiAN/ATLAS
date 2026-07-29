"""Analysis REST endpoints."""

from datetime import datetime

from fastapi import APIRouter, Query, Request

from atlas.domain.models.market_context import MarketContext
from atlas.presentation.api.dtos.market_context import MarketContextDTO
from atlas.presentation.api.schemas import ApiEnvelope, ApiError

router = APIRouter(prefix="/analysis", tags=["analysis"])


def _to_dto(context: MarketContext) -> MarketContextDTO:
    return MarketContextDTO(
        symbol=context.instrument.symbol,
        primary_session=context.primary_session.value,
        active_sessions=[s.value for s in context.active_sessions],
        volatility_regime=context.volatility_regime.value,
        spread_status=context.spread_status.value,
        structural_bias=context.structural_bias.value,
        atr_value=context.atr_value,
        atr_percentile=context.atr_percentile,
        computed_at=context.computed_at,
    )


@router.get("/{symbol}/context")
async def get_market_context(
    request: Request,
    symbol: str,
    as_of: datetime | None = Query(default=None),
    refresh: bool = Query(default=False),
) -> ApiEnvelope[MarketContextDTO]:
    """Current market context snapshot for a symbol."""
    service = request.app.state.container.market_context_service

    if refresh or as_of is not None:
        context = await service.analyze_symbol(symbol, as_of=as_of)
    else:
        context = await service.get_cached(symbol)
        if context is None:
            context = await service.analyze_symbol(symbol)

    if not context:
        return ApiEnvelope(
            success=False,
            data=None,
            error=ApiError(
                code="NOT_FOUND",
                message="Instrument not found or insufficient bar data",
            ),
        )

    return ApiEnvelope(success=True, data=_to_dto(context))
