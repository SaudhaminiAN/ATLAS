"""News filter API DTOs."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class EconomicEventDTO(BaseModel):
    """Economic calendar event."""

    id: str
    name: str
    currency: str
    impact: str
    scheduled_at: datetime
    source: str


class NextEventDTO(BaseModel):
    """Nearest upcoming event."""

    name: str
    scheduled_at: datetime


class NewsFilterStatusDTO(BaseModel):
    """News filter evaluation result."""

    is_blocked: bool
    is_soft_downgrade: bool
    confluence_penalty: Decimal
    next_event: NextEventDTO | None
    as_of: datetime
