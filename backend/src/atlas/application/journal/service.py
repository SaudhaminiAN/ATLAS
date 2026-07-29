"""Trading journal service (Spec 13)."""

from dataclasses import dataclass
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.journal import (
    DecisionFilters,
    JournalEntry,
    PaginatedResult,
    TradeJournalView,
    TradeLifecycleEvent,
)
from atlas.infrastructure.persistence.journal_repository import JournalRepository
from atlas.infrastructure.persistence.repositories import DecisionRepository
from atlas.infrastructure.persistence.trade_repository import TradeRepository

logger = structlog.get_logger(__name__)


@dataclass
class JournalService:
    """Record and query immutable decision and trade history."""

    session_factory: async_sessionmaker[AsyncSession]
    default_user_id: UUID

    async def on_decision(self, decision: TradingDecision) -> None:
        """Idempotently persist a decision with full snapshots."""
        async with self.session_factory() as session:
            inserted = await DecisionRepository(session).insert_idempotent(decision)
            if inserted:
                logger.info(
                    "journal_decision_recorded",
                    decision_id=str(decision.id),
                    symbol=decision.instrument.symbol,
                    direction=decision.direction.value,
                )

    async def on_trade_event(self, event: TradeLifecycleEvent) -> None:
        """Validate and log trade lifecycle events (persisted in trade_events by Spec 11/12)."""
        async with self.session_factory() as session:
            trade = await TradeRepository(session).get(event.trade_id)
            if trade is None:
                logger.warning(
                    "journal_trade_event_orphan",
                    trade_id=str(event.trade_id),
                    event_type=event.event_type,
                )
                return
            logger.info(
                "journal_trade_event_recorded",
                trade_id=str(event.trade_id),
                event_type=event.event_type,
                symbol=trade.instrument.symbol,
            )

    async def add_note(
        self,
        trade_id: UUID,
        content: str,
        tags: list[str] | None = None,
        *,
        user_id: UUID | None = None,
    ) -> JournalEntry:
        """Attach a trader note to an open or closed trade."""
        async with self.session_factory() as session:
            trade_repo = TradeRepository(session)
            trade = await trade_repo.get(trade_id)
            if trade is None:
                raise ValueError("Trade not found")
            journal_repo = JournalRepository(session)
            return await journal_repo.insert_note(
                trade_id=trade_id,
                user_id=user_id or self.default_user_id,
                content=content,
                tags=tags or [],
                decision_id=trade.decision_id,
            )

    async def get_trade_journal(self, trade_id: UUID) -> TradeJournalView:
        """Return trade header, lifecycle events, and notes."""
        async with self.session_factory() as session:
            trade_repo = TradeRepository(session)
            trade = await trade_repo.get(trade_id)
            if trade is None:
                raise ValueError("Trade not found")
            events = await trade_repo.list_events(trade_id)
            notes = await JournalRepository(session).list_by_trade(trade_id)
        return TradeJournalView(
            trade_id=trade.id,
            decision_id=trade.decision_id,
            symbol=trade.instrument.symbol,
            direction=trade.direction.value,
            status=trade.status.value,
            events=tuple(
                {
                    "id": str(e.id),
                    "event_type": e.event_type,
                    "payload": e.payload,
                    "created_at": e.created_at.isoformat(),
                }
                for e in events
            ),
            notes=tuple(notes),
        )

    async def query_decisions(
        self, filters: DecisionFilters
    ) -> PaginatedResult[TradingDecision]:
        """Return filtered paginated decision history."""
        async with self.session_factory() as session:
            repo = DecisionRepository(session)
            items = await repo.query(filters)
            total = await repo.count(filters)
        return PaginatedResult(
            items=tuple(items),
            total=total,
            limit=filters.limit,
            offset=filters.offset,
        )
