"""Execution port interfaces (Spec 11)."""

from typing import Protocol

from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.execution import OrderRequest, OrderResult


class IExecutionProvider(Protocol):
    """Broker or paper execution adapter."""

    async def submit_order(self, request: OrderRequest) -> OrderResult: ...

    async def cancel_order(self, order_id: str) -> OrderResult: ...


class ExecutionServiceProtocol(Protocol):
    """Handle actionable decisions and persist trades."""

    async def on_decision(self, decision: TradingDecision) -> OrderResult | None: ...
