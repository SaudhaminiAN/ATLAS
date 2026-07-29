"""Paper trading execution provider (Spec 11)."""

from decimal import Decimal
from uuid import uuid4

from atlas.domain.models.enums import Direction
from atlas.domain.models.execution import OrderRequest, OrderResult, OrderStatus


class PaperExecutionProvider:
    """Simulate immediate fills with configurable slippage."""

    def __init__(self, slippage_pips: Decimal = Decimal("0.5")) -> None:
        self._slippage_pips = slippage_pips

    async def submit_order(self, request: OrderRequest) -> OrderResult:
        pip_size = request.instrument.pip_size
        slippage = self._slippage_pips * pip_size
        if request.direction == Direction.BUY:
            fill_price = request.entry_price + slippage
        else:
            fill_price = request.entry_price - slippage
        return OrderResult(
            status=OrderStatus.FILLED,
            order_id=str(uuid4()),
            fill_price=fill_price,
            rejection_reason=None,
        )

    async def cancel_order(self, order_id: str) -> OrderResult:
        return OrderResult(
            status=OrderStatus.CANCELLED,
            order_id=order_id,
            fill_price=None,
            rejection_reason=None,
        )
