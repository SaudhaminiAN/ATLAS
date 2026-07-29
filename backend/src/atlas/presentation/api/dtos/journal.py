"""Journal API DTOs."""

from pydantic import BaseModel

from atlas.presentation.api.dtos.decision import TradingDecisionDTO


class PaginatedDecisionsDTO(BaseModel):
    """Paginated decision journal response."""

    items: list[TradingDecisionDTO]
    total: int
    limit: int
    offset: int
