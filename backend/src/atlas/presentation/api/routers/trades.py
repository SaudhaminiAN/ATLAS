"""Trade REST endpoints (Spec 11)."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request

from atlas.domain.models.execution import Trade, TradeStatus
from atlas.presentation.api.dtos.execution import CloseTradeRequest, TradeDTO
from atlas.presentation.api.schemas import ApiEnvelope

router = APIRouter(prefix="/trades", tags=["trades"])


def _to_dto(trade: Trade) -> TradeDTO:
    return TradeDTO(
        id=str(trade.id),
        decision_id=str(trade.decision_id),
        symbol=trade.instrument.symbol,
        direction=trade.direction.value,
        status=trade.status.value,
        entry_price=trade.entry_price,
        fill_price=trade.fill_price,
        stop_loss=trade.stop_loss,
        take_profit=trade.take_profit,
        position_size=trade.position_size,
        execution_mode=trade.execution_mode,
        rejection_reason=trade.rejection_reason,
        opened_at=trade.opened_at,
        closed_at=trade.closed_at,
        realized_pnl=trade.realized_pnl,
        remaining_size=trade.remaining_size,
        partial_realized_pnl=trade.partial_realized_pnl,
    )


@router.get("")
async def list_trades(
    request: Request,
    symbol: str | None = Query(default=None),
    status: TradeStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ApiEnvelope[list[TradeDTO]]:
    """List paper trades."""
    service = request.app.state.container.execution_service
    trades = await service.list_trades(
        symbol=symbol,
        status=status,
        limit=limit,
        offset=offset,
    )
    return ApiEnvelope(success=True, data=[_to_dto(t) for t in trades])


@router.get("/{trade_id}")
async def get_trade(request: Request, trade_id: UUID) -> ApiEnvelope[TradeDTO]:
    """Get a single trade by ID."""
    service = request.app.state.container.execution_service
    trade = await service.get_trade(trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    return ApiEnvelope(success=True, data=_to_dto(trade))


@router.post("/{trade_id}/close")
async def close_trade(
    request: Request,
    trade_id: UUID,
    body: CloseTradeRequest | None = None,
) -> ApiEnvelope[TradeDTO]:
    """Manually close an open paper trade."""
    pm = request.app.state.container.position_management_service
    reason = body.reason if body else "manual"
    try:
        trade = await pm.close_position_manual(trade_id, reason=reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiEnvelope(success=True, data=_to_dto(trade))
