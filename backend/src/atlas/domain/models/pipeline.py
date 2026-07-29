"""Pipeline domain models."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from atlas.domain.models.enums import Timeframe
from atlas.domain.models.instrument import Instrument


class PipelineStatus(StrEnum):
    """Pipeline run lifecycle."""

    SKIPPED = "skipped"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class StageResult:
    """Result of a single pipeline stage."""

    stage_name: str
    status: str
    duration_ms: int = 0
    error: str | None = None


@dataclass
class PipelineRun:
    """Pipeline execution record."""

    id: UUID = field(default_factory=uuid4)
    correlation_id: str = ""
    instrument: Instrument | None = None
    trigger_timeframe: Timeframe = Timeframe.M15
    trigger_bar_time: datetime | None = None
    status: PipelineStatus = PipelineStatus.RUNNING
    stage_results: dict[str, StageResult] = field(default_factory=dict)
    decision_id: UUID | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    duration_ms: int | None = None
