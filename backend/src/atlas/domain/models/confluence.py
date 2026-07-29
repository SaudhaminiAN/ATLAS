"""Confluence domain models."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from atlas.domain.models.enums import Bias, Direction
from atlas.domain.models.instrument import Instrument


@dataclass(frozen=True, slots=True)
class ModuleScore:
    """Per-module directional score contribution."""

    source: str
    direction: Bias
    score: Decimal
    weight: Decimal
    weighted_contribution: Decimal


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    """Evidence item for confluence breakdown."""

    source: str
    direction: Direction
    weight: Decimal
    score: Decimal
    weighted_contribution: Decimal
    description: str


@dataclass(frozen=True, slots=True)
class ConfluenceResult:
    """Weighted confluence output."""

    instrument: Instrument
    suggested_direction: Direction
    total_score: Decimal
    raw_score: Decimal
    bullish_raw: Decimal
    bearish_raw: Decimal
    news_penalty: Decimal
    module_scores: tuple[ModuleScore, ...]
    evidence: tuple[EvidenceItem, ...]
    evidence_count: int
    has_conflict: bool
    strategy_profile_id: str
    computed_at: datetime
