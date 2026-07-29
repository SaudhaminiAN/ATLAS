"""Position management application service (Spec 12)."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from atlas.application.market_data.service import MarketDataService
from atlas.domain.events.base import DomainEvent
from atlas.domain.models.enums import Timeframe
from atlas.domain.models.execution import Trade, TradeEvent, TradeStatus
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.position_management import (
    ActionType,
    PositionAction,
    PositionManagementConfig,
    PositionState,
    PositionStatus,
)
from atlas.domain.ports.event_bus import EventBusProtocol
from atlas.domain.services.bar_validation import compute_atr
from atlas.domain.services.position_management import evaluate_bar, manual_close_action
from atlas.infrastructure.persistence.trade_repository import TradeRepository

logger = structlog.get_logger(__name__)


def _entry_for_trade(trade: Trade) -> Decimal:
    return trade.fill_price if trade.fill_price is not None else trade.entry_price


def trade_to_position_state(trade: Trade) -> PositionState:
    entry = _entry_for_trade(trade)
    initial_sl = trade.initial_stop_loss or trade.stop_loss
    remaining = trade.remaining_size if trade.remaining_size is not None else trade.position_size
    if trade.status == TradeStatus.PARTIAL:
        pos_status = PositionStatus.PARTIAL
    elif trade.status == TradeStatus.OPEN:
        pos_status = PositionStatus.OPEN
    else:
        pos_status = PositionStatus.CLOSED
    return PositionState(
        trade_id=trade.id,
        direction=trade.direction,
        entry_price=entry,
        initial_stop_loss=initial_sl,
        current_sl=trade.stop_loss,
        current_tp=trade.take_profit,
        position_size=trade.position_size,
        remaining_size=remaining,
        partial_realized_pnl=trade.partial_realized_pnl,
        breakeven_applied=trade.breakeven_applied,
        partial_exit_applied=trade.partial_exit_applied,
        status=pos_status,
    )


def position_state_to_trade(trade: Trade, state: PositionState, closed_at: datetime | None) -> Trade:
    if state.status == PositionStatus.CLOSED:
        trade_status = TradeStatus.CLOSED
        realized = state.partial_realized_pnl
    elif state.status == PositionStatus.PARTIAL:
        trade_status = TradeStatus.PARTIAL
        realized = None
    else:
        trade_status = TradeStatus.OPEN
        realized = None
    return Trade(
        id=trade.id,
        decision_id=trade.decision_id,
        instrument=trade.instrument,
        direction=trade.direction,
        status=trade_status,
        entry_price=trade.entry_price,
        fill_price=trade.fill_price,
        stop_loss=state.current_sl,
        take_profit=state.current_tp,
        position_size=trade.position_size,
        execution_mode=trade.execution_mode,
        rejection_reason=trade.rejection_reason,
        opened_at=trade.opened_at,
        closed_at=closed_at if state.status == PositionStatus.CLOSED else None,
        realized_pnl=realized,
        initial_stop_loss=state.initial_stop_loss,
        remaining_size=state.remaining_size,
        partial_realized_pnl=state.partial_realized_pnl,
        breakeven_applied=state.breakeven_applied,
        partial_exit_applied=state.partial_exit_applied,
    )


@dataclass
class PositionManagementService:
    """Monitor open trades on each primary-timeframe bar."""

    session_factory: async_sessionmaker[AsyncSession]
    market_data_service: MarketDataService
    event_bus: EventBusProtocol
    config: PositionManagementConfig
    primary_timeframe: Timeframe
    atr_period: int = 14

    async def on_bar(self, symbol: str, timeframe: str) -> list[PositionAction]:
        """Process open positions for the given symbol and timeframe."""
        if timeframe != self.primary_timeframe.value:
            return []
        instrument = await self.market_data_service.get_instrument(symbol)
        if instrument is None:
            return []
        bar = await self.market_data_service.get_latest(instrument, self.primary_timeframe)
        if bar is None:
            logger.warning("position_mgmt_no_bar", symbol=symbol)
            return []
        return await self._process_bar(symbol, bar)

    async def close_position_manual(self, trade_id: UUID, reason: str = "manual") -> Trade:
        """Close an open trade at the latest bar close."""
        async with self.session_factory() as session:
            repo = TradeRepository(session)
            trade = await repo.get(trade_id)
            if trade is None:
                raise ValueError("Trade not found")
            if trade.status not in (TradeStatus.OPEN, TradeStatus.PARTIAL):
                raise ValueError("Trade is not open")
            bar = await self.market_data_service.get_latest(
                trade.instrument, self.primary_timeframe
            )
            if bar is None:
                raise ValueError("No market bar available for close")
            state = trade_to_position_state(trade)
            new_state, action = manual_close_action(state, bar, reason)
            updated = position_state_to_trade(trade, new_state, datetime.now(UTC))
            await repo.update(updated)
            await self._record_actions(repo, trade, [action], updated)
            self._publish_events(trade, [action], updated)
            return updated

    async def _process_bar(self, symbol: str, bar: OHLCVBar) -> list[PositionAction]:
        async with self.session_factory() as session:
            repo = TradeRepository(session)
            open_trades = await repo.list_open_trades(symbol)
            if not open_trades:
                return []

            atr = await self._compute_atr(bar.instrument, bar.open_time)
            all_actions: list[PositionAction] = []

            for trade in open_trades:
                state = trade_to_position_state(trade)
                new_state, actions = evaluate_bar(state, bar, atr, self.config)
                if not actions:
                    continue
                closed_at = datetime.now(UTC) if new_state.status == PositionStatus.CLOSED else None
                updated = position_state_to_trade(trade, new_state, closed_at)
                await repo.update(updated)
                await self._record_actions(repo, trade, actions, updated)
                self._publish_events(trade, actions, updated)
                all_actions.extend(actions)
                logger.info(
                    "position_mgmt_actions",
                    trade_id=str(trade.id),
                    actions=[a.action_type.value for a in actions],
                )
            return all_actions

    async def _compute_atr(self, instrument, as_of: datetime) -> Decimal | None:
        bars = await self.market_data_service.get_recent_bars(
            instrument,
            self.primary_timeframe,
            limit=self.atr_period + 1,
            as_of=as_of,
        )
        if len(bars) < self.atr_period:
            return None
        return compute_atr(bars, self.atr_period)

    async def _record_actions(
        self,
        repo: TradeRepository,
        trade: Trade,
        actions: list[PositionAction],
        updated: Trade,
    ) -> None:
        now = datetime.now(UTC)
        for action in actions:
            event_type = self._event_type_for_action(action)
            payload = {
                "action": action.action_type.value,
                "reason": action.reason,
                "old_sl": str(action.old_sl) if action.old_sl is not None else None,
                "new_sl": str(action.new_sl) if action.new_sl is not None else None,
                "closed_size": str(action.closed_size) if action.closed_size is not None else None,
                "close_price": str(action.close_price) if action.close_price is not None else None,
                "bar_time": action.bar_time.isoformat(),
                "symbol": trade.instrument.symbol,
            }
            if action.realized_pnl_delta is not None:
                payload["realized_pnl_delta"] = str(action.realized_pnl_delta)
            if updated.realized_pnl is not None and action.action_type == ActionType.CLOSE:
                payload["total_realized_pnl"] = str(updated.realized_pnl)
            await repo.append_event(
                TradeEvent(
                    id=uuid4(),
                    trade_id=trade.id,
                    event_type=event_type,
                    payload=payload,
                    created_at=now,
                )
            )

    def _event_type_for_action(self, action: PositionAction) -> str:
        if action.action_type == ActionType.BREAKEVEN:
            return "sl_moved"
        if action.action_type == ActionType.TRAIL_SL:
            return "sl_moved"
        if action.action_type == ActionType.PARTIAL_CLOSE:
            return "partial_closed"
        return "closed"

    def _publish_events(
        self, trade: Trade, actions: list[PositionAction], updated: Trade
    ) -> None:
        for action in actions:
            bus_type = {
                ActionType.BREAKEVEN: "trade.sl_moved",
                ActionType.TRAIL_SL: "trade.sl_moved",
                ActionType.PARTIAL_CLOSE: "trade.partial_closed",
                ActionType.CLOSE: "trade.closed",
            }[action.action_type]
            self.event_bus.publish(
                DomainEvent(
                    event_type=bus_type,
                    correlation_id=f"trade-{trade.id}",
                    payload={
                        "trade_id": str(trade.id),
                        "symbol": trade.instrument.symbol,
                        "direction": trade.direction.value,
                        "action": action.action_type.value,
                        "reason": action.reason,
                        "status": updated.status.value,
                        "stop_loss": str(updated.stop_loss),
                        "take_profit": str(updated.take_profit),
                        "remaining_size": str(updated.remaining_size),
                        "realized_pnl": (
                            str(updated.realized_pnl) if updated.realized_pnl is not None else None
                        ),
                    },
                )
            )
