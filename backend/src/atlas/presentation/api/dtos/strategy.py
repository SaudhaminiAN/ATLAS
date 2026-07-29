"""Strategy API DTOs."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class StrategyProfileDTO(BaseModel):
    """Strategy profile response."""

    id: str
    name: str
    min_confluence_score: Decimal
    enabled_directions: list[str]
    confluence_weights: dict[str, Decimal]
    active_timeframes: list[str]
    allowed_sessions: list[str]
    validation_rule_flags: dict[str, bool] = Field(serialization_alias="validation_rules")
    is_active: bool
    updated_at: datetime

    model_config = {"populate_by_name": True}


class SetActiveProfileRequest(BaseModel):
    """Request body for switching active profile."""

    profile_id: str
