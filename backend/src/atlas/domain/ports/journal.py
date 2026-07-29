"""Journal service port."""

from typing import Protocol

from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.journal import DecisionFilters, PaginatedResult


class JournalServiceProtocol(Protocol):
    """Immutable record of decisions and trade lifecycle events."""

    async def on_decision(self, decision: TradingDecision) -> None:
        """Persist a decision idempotently (all directions including WAIT)."""
        ...

    async def query_decisions(
        self, filters: DecisionFilters
    ) -> PaginatedResult[TradingDecision]:
        """Return filtered, paginated decision history."""
        ...
