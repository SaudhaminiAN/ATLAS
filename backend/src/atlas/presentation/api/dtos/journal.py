"""Journal API DTOs."""

from datetime import datetime

from pydantic import BaseModel, Field

from atlas.presentation.api.dtos.decision import TradingDecisionDTO


class PaginatedDecisionsDTO(BaseModel):
    """Paginated decision journal response."""

    items: list[TradingDecisionDTO]
    total: int
    limit: int
    offset: int


class JournalEntryDTO(BaseModel):
    id: str
    decision_id: str | None
    trade_id: str | None
    user_id: str
    entry_type: str
    content: str
    tags: list[str]
    created_at: datetime


class TradeJournalEventDTO(BaseModel):
    id: str
    event_type: str
    payload: dict
    created_at: str


class TradeJournalDTO(BaseModel):
    trade_id: str
    decision_id: str
    symbol: str
    direction: str
    status: str
    events: list[TradeJournalEventDTO]
    notes: list[JournalEntryDTO]


class AddNoteRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    tags: list[str] = Field(default_factory=list)
