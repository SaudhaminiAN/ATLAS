"""Journal service port."""

from typing import Protocol
from uuid import UUID

from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.journal import (
    DecisionFilters,
    JournalEntry,
    PaginatedResult,
    TradeJournalView,
    TradeLifecycleEvent,
)


class JournalServiceProtocol(Protocol):
    """Immutable record of decisions and trade lifecycle events."""

    async def on_decision(self, decision: TradingDecision) -> None:
        """Persist a decision idempotently (all directions including WAIT)."""
        ...

    async def on_trade_event(self, event: TradeLifecycleEvent) -> None:
        """Record trade lifecycle event in journal."""
        ...

    async def add_note(
        self,
        trade_id: UUID,
        content: str,
        tags: list[str] | None = None,
    ) -> JournalEntry:
        """Attach a trader note to a trade."""
        ...

    async def get_trade_journal(self, trade_id: UUID) -> TradeJournalView:
        """Return trade header, events, and notes."""
        ...

    async def query_decisions(
        self, filters: DecisionFilters
    ) -> PaginatedResult[TradingDecision]:
        """Return filtered, paginated decision history."""
        ...
