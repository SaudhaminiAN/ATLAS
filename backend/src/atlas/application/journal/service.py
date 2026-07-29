"""Trading journal service (Spec 13, Phase 1)."""

from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.journal import DecisionFilters, PaginatedResult
from atlas.infrastructure.persistence.repositories import DecisionRepository

logger = structlog.get_logger(__name__)


@dataclass
class JournalService:
    """Record and query immutable decision history."""

    session_factory: async_sessionmaker[AsyncSession]

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
