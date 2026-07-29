"""News filter REST endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Query, Request

from atlas.domain.models.news import EconomicEvent, NewsFilterStatus
from atlas.presentation.api.dtos.news import (
    EconomicEventDTO,
    NewsFilterStatusDTO,
    NextEventDTO,
)
from atlas.presentation.api.schemas import ApiEnvelope

router = APIRouter(prefix="/news", tags=["news"])


def _event_to_dto(event: EconomicEvent) -> EconomicEventDTO:
    return EconomicEventDTO(
        id=str(event.id),
        name=event.name,
        currency=event.currency,
        impact=event.impact.value,
        scheduled_at=event.scheduled_at,
        source=event.source,
    )


def _status_to_dto(status: NewsFilterStatus) -> NewsFilterStatusDTO:
    next_event = None
    if status.next_event:
        next_event = NextEventDTO(
            name=status.next_event.name,
            scheduled_at=status.next_event.scheduled_at,
        )
    return NewsFilterStatusDTO(
        is_blocked=status.is_blocked,
        is_soft_downgrade=status.is_soft_downgrade,
        confluence_penalty=status.confluence_penalty,
        next_event=next_event,
        as_of=status.as_of,
    )


@router.get("/upcoming")
async def get_upcoming_events(
    request: Request,
    hours: int = Query(default=24, ge=1, le=168),
) -> ApiEnvelope[list[EconomicEventDTO]]:
    """Upcoming high-impact economic events."""
    service = request.app.state.container.news_filter
    events = await service.get_upcoming(hours=hours)
    return ApiEnvelope(success=True, data=[_event_to_dto(e) for e in events])


@router.get("/status")
async def get_news_status(
    request: Request,
    as_of: datetime | None = Query(default=None),
) -> ApiEnvelope[NewsFilterStatusDTO]:
    """Current news filter status (optional as_of for backtest)."""
    service = request.app.state.container.news_filter
    check_time = as_of or datetime.now(UTC)
    status = service.check(check_time)
    return ApiEnvelope(success=True, data=_status_to_dto(status))
