"""Decision API DTOs."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from atlas.presentation.api.dtos.confluence import ConfluenceDTO
from atlas.presentation.api.dtos.validation import ValidationResultDTO


class NewsStatusDTO(BaseModel):
    """News filter snapshot at decision time."""

    is_blocked: bool
    is_soft_downgrade: bool
    confluence_penalty: Decimal
    next_event_name: str | None = None
    next_event_at: datetime | None = None
    as_of: datetime


class TradingDecisionDTO(BaseModel):
    """Trading decision response."""

    id: UUID
    symbol: str
    direction: str
    is_actionable: bool
    confluence_score: Decimal
    strategy_id: str
    reason: str
    correlation_id: str
    decided_at: datetime
    confluence_snapshot: ConfluenceDTO | None = None
    validation_snapshot: ValidationResultDTO | None = None
    risk_snapshot: dict | None = None
    news_status: NewsStatusDTO | None = None
