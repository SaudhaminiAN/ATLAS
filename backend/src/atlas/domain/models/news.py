"""News filter domain models."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class EventImpact(StrEnum):
    """Economic event impact level."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class EconomicEvent:
    """Scheduled economic calendar event (UTC)."""

    id: UUID
    name: str
    currency: str
    impact: EventImpact
    scheduled_at: datetime
    source: str
    actual: Decimal | None = None
    forecast: Decimal | None = None
    previous: Decimal | None = None


@dataclass(frozen=True, slots=True)
class NextEventInfo:
    """Nearest upcoming high-impact event."""

    name: str
    scheduled_at: datetime


@dataclass(frozen=True, slots=True)
class NewsFilterStatus:
    """News filter evaluation at a point in time."""

    is_blocked: bool
    is_soft_downgrade: bool
    confluence_penalty: Decimal
    next_event: NextEventInfo | None
    as_of: datetime
