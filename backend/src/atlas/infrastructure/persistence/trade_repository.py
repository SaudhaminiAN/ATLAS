"""Trade persistence (Spec 11 + 12)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from atlas.domain.models.enums import Direction
from atlas.domain.models.execution import Trade, TradeEvent, TradeStatus
from atlas.domain.models.instrument import Instrument
from atlas.infrastructure.persistence.models import TradeEventModel, TradeModel
from atlas.infrastructure.persistence.repositories import instrument_to_domain


def trade_to_domain(model: TradeModel, instrument: Instrument) -> Trade:
    return Trade(
        id=model.id,
        decision_id=model.decision_id,
        instrument=instrument,
        direction=Direction(model.direction),
        status=TradeStatus(model.status),
        entry_price=Decimal(str(model.entry_price)),
        fill_price=Decimal(str(model.fill_price)) if model.fill_price is not None else None,
        stop_loss=Decimal(str(model.stop_loss)),
        take_profit=Decimal(str(model.take_profit)),
        position_size=Decimal(str(model.position_size)),
        execution_mode=model.execution_mode,
        rejection_reason=model.rejection_reason,
        opened_at=model.opened_at,
        closed_at=model.closed_at,
        realized_pnl=(
            Decimal(str(model.realized_pnl)) if model.realized_pnl is not None else None
        ),
        initial_stop_loss=(
            Decimal(str(model.initial_stop_loss))
            if model.initial_stop_loss is not None
            else None
        ),
        remaining_size=(
            Decimal(str(model.remaining_size)) if model.remaining_size is not None else None
        ),
        partial_realized_pnl=Decimal(str(model.partial_realized_pnl)),
        breakeven_applied=bool(model.breakeven_applied),
        partial_exit_applied=bool(model.partial_exit_applied),
    )


class TradeRepository:
    """Trade and trade_event persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_decision_id(self, decision_id: UUID) -> Trade | None:
        result = await self._session.execute(
            select(TradeModel).where(TradeModel.decision_id == decision_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        instrument = await self._load_instrument(row.instrument_id)
        return trade_to_domain(row, instrument)

    async def insert(self, trade: Trade) -> bool:
        remaining = trade.remaining_size if trade.remaining_size is not None else trade.position_size
        initial_sl = (
            trade.initial_stop_loss if trade.initial_stop_loss is not None else trade.stop_loss
        )
        stmt = (
            insert(TradeModel)
            .values(
                id=trade.id,
                decision_id=trade.decision_id,
                instrument_id=trade.instrument.id,
                direction=trade.direction.value,
                status=trade.status.value,
                entry_price=trade.entry_price,
                fill_price=trade.fill_price,
                stop_loss=trade.stop_loss,
                take_profit=trade.take_profit,
                position_size=trade.position_size,
                execution_mode=trade.execution_mode,
                rejection_reason=trade.rejection_reason,
                realized_pnl=trade.realized_pnl,
                initial_stop_loss=initial_sl,
                remaining_size=remaining,
                partial_realized_pnl=trade.partial_realized_pnl,
                breakeven_applied=trade.breakeven_applied,
                partial_exit_applied=trade.partial_exit_applied,
                opened_at=trade.opened_at,
                closed_at=trade.closed_at,
            )
            .on_conflict_do_nothing(index_elements=["decision_id"])
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount > 0

    async def update(self, trade: Trade) -> None:
        await self._session.execute(
            update(TradeModel)
            .where(TradeModel.id == trade.id)
            .values(
                status=trade.status.value,
                stop_loss=trade.stop_loss,
                take_profit=trade.take_profit,
                remaining_size=trade.remaining_size,
                partial_realized_pnl=trade.partial_realized_pnl,
                breakeven_applied=trade.breakeven_applied,
                partial_exit_applied=trade.partial_exit_applied,
                realized_pnl=trade.realized_pnl,
                closed_at=trade.closed_at,
            )
        )
        await self._session.commit()

    async def append_event(self, event: TradeEvent) -> None:
        model = TradeEventModel(
            id=event.id,
            trade_id=event.trade_id,
            event_type=event.event_type,
            payload=event.payload,
            created_at=event.created_at,
        )
        self._session.add(model)
        await self._session.commit()

    async def list_events(self, trade_id: UUID) -> list[TradeEvent]:
        result = await self._session.execute(
            select(TradeEventModel)
            .where(TradeEventModel.trade_id == trade_id)
            .order_by(TradeEventModel.created_at.asc())
        )
        return [
            TradeEvent(
                id=row.id,
                trade_id=row.trade_id,
                event_type=row.event_type,
                payload=row.payload,
                created_at=row.created_at,
            )
            for row in result.scalars().all()
        ]

    async def list_trades(
        self,
        *,
        symbol: str | None = None,
        status: TradeStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Trade]:
        from atlas.infrastructure.persistence.models import InstrumentModel

        query = (
            select(TradeModel, InstrumentModel)
            .join(InstrumentModel, TradeModel.instrument_id == InstrumentModel.id)
            .order_by(TradeModel.opened_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if symbol:
            query = query.where(InstrumentModel.symbol == symbol.upper())
        if status:
            query = query.where(TradeModel.status == status.value)
        result = await self._session.execute(query)
        return [
            trade_to_domain(trade_model, instrument_to_domain(instrument_model))
            for trade_model, instrument_model in result.all()
        ]

    async def list_open_trades(self, symbol: str | None = None) -> list[Trade]:
        from atlas.infrastructure.persistence.models import InstrumentModel

        query = (
            select(TradeModel, InstrumentModel)
            .join(InstrumentModel, TradeModel.instrument_id == InstrumentModel.id)
            .where(TradeModel.status.in_([TradeStatus.OPEN.value, TradeStatus.PARTIAL.value]))
            .order_by(TradeModel.opened_at.asc())
        )
        if symbol:
            query = query.where(InstrumentModel.symbol == symbol.upper())
        result = await self._session.execute(query)
        return [
            trade_to_domain(trade_model, instrument_to_domain(instrument_model))
            for trade_model, instrument_model in result.all()
        ]

    async def get(self, trade_id: UUID) -> Trade | None:
        from atlas.infrastructure.persistence.models import InstrumentModel

        result = await self._session.execute(
            select(TradeModel, InstrumentModel)
            .join(InstrumentModel, TradeModel.instrument_id == InstrumentModel.id)
            .where(TradeModel.id == trade_id)
        )
        row = result.first()
        if not row:
            return None
        trade_model, instrument_model = row
        return trade_to_domain(trade_model, instrument_to_domain(instrument_model))

    async def _load_instrument(self, instrument_id: UUID) -> Instrument:
        from atlas.infrastructure.persistence.models import InstrumentModel

        result = await self._session.execute(
            select(InstrumentModel).where(InstrumentModel.id == instrument_id)
        )
        model = result.scalar_one()
        return instrument_to_domain(model)
