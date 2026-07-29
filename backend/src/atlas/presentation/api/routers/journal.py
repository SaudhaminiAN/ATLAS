"""Journal REST endpoints (Spec 13)."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request

from atlas.domain.models.enums import Direction
from atlas.domain.models.journal import DecisionFilters, JournalEntry
from atlas.presentation.api.dtos.journal import (
    AddNoteRequest,
    JournalEntryDTO,
    PaginatedDecisionsDTO,
    TradeJournalDTO,
    TradeJournalEventDTO,
)
from atlas.presentation.api.routers.decisions import _to_dto
from atlas.presentation.api.schemas import ApiEnvelope

router = APIRouter(prefix="/journal", tags=["journal"])


def _entry_to_dto(entry: JournalEntry) -> JournalEntryDTO:
    return JournalEntryDTO(
        id=str(entry.id),
        decision_id=str(entry.decision_id) if entry.decision_id else None,
        trade_id=str(entry.trade_id) if entry.trade_id else None,
        user_id=str(entry.user_id),
        entry_type=entry.entry_type,
        content=entry.content,
        tags=list(entry.tags),
        created_at=entry.created_at,
    )


@router.get("/decisions")
async def query_decisions(
    request: Request,
    symbol: str | None = Query(default=None),
    direction: Direction | None = Query(default=None),
    is_actionable: bool | None = Query(default=None),
    correlation_id: str | None = Query(default=None),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ApiEnvelope[PaginatedDecisionsDTO]:
    """Filtered, paginated decision journal history."""
    service = request.app.state.container.journal_service
    result = await service.query_decisions(
        DecisionFilters(
            symbol=symbol,
            direction=direction,
            is_actionable=is_actionable,
            correlation_id=correlation_id,
            start=start,
            end=end,
            limit=limit,
            offset=offset,
        )
    )
    return ApiEnvelope(
        success=True,
        data=PaginatedDecisionsDTO(
            items=[_to_dto(item) for item in result.items],
            total=result.total,
            limit=result.limit,
            offset=result.offset,
        ),
    )


@router.get("/trades/{trade_id}")
async def get_trade_journal(request: Request, trade_id: UUID) -> ApiEnvelope[TradeJournalDTO]:
    """Full trade lifecycle: header, events, and notes."""
    service = request.app.state.container.journal_service
    try:
        view = await service.get_trade_journal(trade_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiEnvelope(
        success=True,
        data=TradeJournalDTO(
            trade_id=str(view.trade_id),
            decision_id=str(view.decision_id),
            symbol=view.symbol,
            direction=view.direction,
            status=view.status,
            events=[
                TradeJournalEventDTO(
                    id=e["id"],
                    event_type=e["event_type"],
                    payload=e["payload"],
                    created_at=e["created_at"],
                )
                for e in view.events
            ],
            notes=[_entry_to_dto(n) for n in view.notes],
        ),
    )


@router.post("/trades/{trade_id}/notes")
async def add_trade_note(
    request: Request,
    trade_id: UUID,
    body: AddNoteRequest,
) -> ApiEnvelope[JournalEntryDTO]:
    """Attach a trader note to a trade."""
    service = request.app.state.container.journal_service
    try:
        entry = await service.add_note(trade_id, body.content, body.tags)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiEnvelope(success=True, data=_entry_to_dto(entry))
