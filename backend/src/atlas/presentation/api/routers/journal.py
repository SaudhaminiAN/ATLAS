"""Journal REST endpoints (Spec 13, Phase 1)."""

from datetime import datetime

from fastapi import APIRouter, Query, Request

from atlas.domain.models.enums import Direction
from atlas.domain.models.journal import DecisionFilters
from atlas.presentation.api.dtos.journal import PaginatedDecisionsDTO
from atlas.presentation.api.routers.decisions import _to_dto
from atlas.presentation.api.schemas import ApiEnvelope

router = APIRouter(prefix="/journal", tags=["journal"])


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
