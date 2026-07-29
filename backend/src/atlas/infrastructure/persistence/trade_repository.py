"""Trade persistence (Spec 11)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
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
                opened_at=trade.opened_at,
                closed_at=trade.closed_at,
            )
            .on_conflict_do_nothing(index_elements=["decision_id"])
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount > 0

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
