"""Confluence API DTOs."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ModuleScoreDTO(BaseModel):
    """Per-module confluence contribution."""

    source: str
    direction: str
    score: Decimal
    weight: Decimal
    weighted_contribution: Decimal


class EvidenceItemDTO(BaseModel):
    """Confluence evidence item."""

    source: str
    direction: str
    weight: Decimal
    score: Decimal
    weighted_contribution: Decimal
    description: str


class ConfluenceDTO(BaseModel):
    """Confluence analysis snapshot."""

    symbol: str
    suggested_direction: str
    total_score: Decimal
    raw_score: Decimal
    bullish_raw: Decimal
    bearish_raw: Decimal
    news_penalty: Decimal
    module_scores: list[ModuleScoreDTO]
    evidence: list[EvidenceItemDTO]
    evidence_count: int
    has_conflict: bool
    strategy_profile_id: str
    computed_at: datetime
