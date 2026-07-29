"""Journal domain models."""

from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from atlas.domain.models.enums import Direction

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class DecisionFilters:
    """Query filters for decision journal history."""

    symbol: str | None = None
    direction: Direction | None = None
    is_actionable: bool | None = None
    correlation_id: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True, slots=True)
class PaginatedResult(Generic[T]):
    """Paginated query result."""

    items: tuple[T, ...]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class JournalEntry:
    """Trader note attached to a decision or trade (Phase 3)."""

    id: UUID
    decision_id: UUID | None
    trade_id: UUID | None
    user_id: UUID
    entry_type: str
    content: str
    tags: tuple[str, ...]
    created_at: datetime
