"""Execution application service (Spec 11)."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from atlas.domain.events.base import DomainEvent
from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.execution import (
    OrderRequest,
    OrderResult,
    OrderStatus,
    Trade,
    TradeEvent,
    TradeStatus,
)
from atlas.domain.ports.event_bus import EventBusProtocol
from atlas.domain.ports.execution import IExecutionProvider
from atlas.infrastructure.cache.execution_idempotency import ExecutionIdempotencyCache
from atlas.infrastructure.persistence.trade_repository import TradeRepository

logger = structlog.get_logger(__name__)


def _params_from_risk_snapshot(decision: TradingDecision) -> dict[str, Decimal] | None:
    snapshot = decision.risk_snapshot
    if not snapshot or not snapshot.get("within_limits"):
        return None
    raw = snapshot.get("parameters")
    if not raw:
        return None
    return {
        "entry_price": Decimal(str(raw["entry_price"])),
        "stop_loss": Decimal(str(raw["stop_loss"])),
        "take_profit": Decimal(str(raw["take_profit"])),
        "position_size": Decimal(str(raw["position_size"])),
    }


@dataclass
class ExecutionService:
    """Submit paper orders for actionable decisions."""

    session_factory: async_sessionmaker[AsyncSession]
    provider: IExecutionProvider
    idempotency_cache: ExecutionIdempotencyCache
    event_bus: EventBusProtocol
    execution_mode: str = "paper"

    async def on_decision(self, decision: TradingDecision) -> OrderResult | None:
        """Process an actionable decision; skip WAIT silently."""
        if not decision.is_actionable:
            return None

        if self.execution_mode == "live":
            return await self._reject(decision, "Live execution not enabled")

        params = _params_from_risk_snapshot(decision)
        if params is None:
            return await self._reject(decision, "Missing risk parameters")

        idempotency_key = str(decision.id)
        existing = await self._get_existing_trade(decision.id)
        if existing is not None:
            return OrderResult(
                status=OrderStatus.FILLED if existing.status == TradeStatus.OPEN else OrderStatus.REJECTED,
                order_id=str(existing.id),
                fill_price=existing.fill_price,
                rejection_reason=existing.rejection_reason,
            )

        acquired = await self.idempotency_cache.try_acquire(idempotency_key)
        if not acquired:
            existing = await self._get_existing_trade(decision.id)
            if existing:
                return OrderResult(
                    status=OrderStatus.FILLED,
                    order_id=str(existing.id),
                    fill_price=existing.fill_price,
                    rejection_reason=None,
                )
            return None

        request = OrderRequest(
            decision_id=decision.id,
            instrument=decision.instrument,
            direction=decision.direction,
            entry_price=params["entry_price"],
            stop_loss=params["stop_loss"],
            take_profit=params["take_profit"],
            position_size=params["position_size"],
            idempotency_key=idempotency_key,
        )

        try:
            result = await self.provider.submit_order(request)
        except Exception as exc:
            logger.exception("execution_provider_failed", decision_id=str(decision.id))
            return await self._reject(decision, f"Provider error: {exc}")

        if result.status == OrderStatus.FILLED:
            await self._persist_open_trade(decision, request, result)
            self._publish("trade.opened", decision, result)
            logger.info(
                "trade_opened",
                decision_id=str(decision.id),
                symbol=decision.instrument.symbol,
                fill=str(result.fill_price),
            )
            return result

        return await self._reject(decision, result.rejection_reason or "Order rejected")

    async def _reject(self, decision: TradingDecision, reason: str) -> OrderResult:
        result = OrderResult(
            status=OrderStatus.REJECTED,
            order_id=None,
            fill_price=None,
            rejection_reason=reason,
        )
        await self._persist_rejected_trade(decision, reason)
        self._publish("trade.rejected", decision, result)
        logger.warning("trade_rejected", decision_id=str(decision.id), reason=reason)
        return result

    async def _get_existing_trade(self, decision_id: UUID) -> Trade | None:
        async with self.session_factory() as session:
            return await TradeRepository(session).get_by_decision_id(decision_id)

    async def _persist_open_trade(
        self,
        decision: TradingDecision,
        request: OrderRequest,
        result: OrderResult,
    ) -> None:
        now = datetime.now(UTC)
        trade = Trade(
            id=uuid4(),
            decision_id=decision.id,
            instrument=decision.instrument,
            direction=decision.direction,
            status=TradeStatus.OPEN,
            entry_price=request.entry_price,
            fill_price=result.fill_price,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
            position_size=request.position_size,
            execution_mode=self.execution_mode,
            rejection_reason=None,
            opened_at=now,
            closed_at=None,
            realized_pnl=None,
        )
        async with self.session_factory() as session:
            repo = TradeRepository(session)
            await repo.insert(trade)
            await repo.append_event(
                TradeEvent(
                    id=uuid4(),
                    trade_id=trade.id,
                    event_type="opened",
                    payload={
                        "decision_id": str(decision.id),
                        "fill_price": str(result.fill_price),
                        "direction": decision.direction.value,
                    },
                    created_at=now,
                )
            )

    async def _persist_rejected_trade(self, decision: TradingDecision, reason: str) -> None:
        params = _params_from_risk_snapshot(decision)
        now = datetime.now(UTC)
        trade = Trade(
            id=uuid4(),
            decision_id=decision.id,
            instrument=decision.instrument,
            direction=decision.direction,
            status=TradeStatus.REJECTED,
            entry_price=params["entry_price"] if params else Decimal("0"),
            fill_price=None,
            stop_loss=params["stop_loss"] if params else Decimal("0"),
            take_profit=params["take_profit"] if params else Decimal("0"),
            position_size=params["position_size"] if params else Decimal("0"),
            execution_mode=self.execution_mode,
            rejection_reason=reason,
            opened_at=now,
            closed_at=now,
            realized_pnl=None,
        )
        async with self.session_factory() as session:
            repo = TradeRepository(session)
            await repo.insert(trade)
            await repo.append_event(
                TradeEvent(
                    id=uuid4(),
                    trade_id=trade.id,
                    event_type="rejected",
                    payload={"reason": reason, "decision_id": str(decision.id)},
                    created_at=now,
                )
            )

    def _publish(self, event_type: str, decision: TradingDecision, result: OrderResult) -> None:
        self.event_bus.publish(
            DomainEvent(
                event_type=event_type,
                correlation_id=decision.correlation_id,
                payload={
                    "decision_id": str(decision.id),
                    "symbol": decision.instrument.symbol,
                    "direction": decision.direction.value,
                    "status": result.status.value,
                    "fill_price": str(result.fill_price) if result.fill_price else None,
                    "rejection_reason": result.rejection_reason,
                },
            )
        )

    async def list_trades(
        self,
        *,
        symbol: str | None = None,
        status: TradeStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Trade]:
        async with self.session_factory() as session:
            return await TradeRepository(session).list_trades(
                symbol=symbol,
                status=status,
                limit=limit,
                offset=offset,
            )

    async def get_trade(self, trade_id: UUID) -> Trade | None:
        async with self.session_factory() as session:
            return await TradeRepository(session).get(trade_id)
