"""Paper execution provider tests."""

from decimal import Decimal
from uuid import uuid4

import pytest

from atlas.domain.models.enums import Direction
from atlas.domain.models.execution import OrderRequest, OrderStatus
from atlas.domain.models.instrument import Instrument
from atlas.infrastructure.execution.paper_provider import PaperExecutionProvider


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


@pytest.mark.asyncio
async def test_paper_fill_applies_slippage() -> None:
    provider = PaperExecutionProvider(slippage_pips=Decimal("0.5"))
    request = OrderRequest(
        decision_id=uuid4(),
        instrument=_instrument(),
        direction=Direction.BUY,
        entry_price=Decimal("2350"),
        stop_loss=Decimal("2340"),
        take_profit=Decimal("2370"),
        position_size=Decimal("0.10"),
        idempotency_key="test",
    )
    result = await provider.submit_order(request)
    assert result.status == OrderStatus.FILLED
    assert result.fill_price == Decimal("2350.005")
