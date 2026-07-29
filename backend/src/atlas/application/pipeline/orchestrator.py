"""Analysis pipeline orchestrator (stub for Spec 20)."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

import structlog

from atlas.domain.events.base import DomainEvent
from atlas.domain.ports.event_bus import EventBusProtocol

logger = structlog.get_logger(__name__)


class PipelineStatus(StrEnum):
    """Pipeline run lifecycle."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class StageResult:
    """Result of a single pipeline stage."""

    stage_name: str
    status: str
    duration_ms: int = 0
    error: str | None = None


@dataclass
class PipelineRun:
    """Pipeline execution record."""

    correlation_id: str
    status: PipelineStatus
    stage_results: dict[str, StageResult] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class AnalysisPipelineOrchestrator:
    """Stub orchestrator — stages wired in Spec 20."""

    STAGES: tuple[str, ...] = (
        "market_context",
        "mtf_analysis",
        "technical_analysis",
        "smc_analysis",
        "price_action",
        "news_filter",
        "confluence",
        "validation",
        "risk",
        "decision_engine",
    )

    def __init__(self, event_bus: EventBusProtocol, risk_enabled: bool = False) -> None:
        self._event_bus = event_bus
        self._risk_enabled = risk_enabled

    async def run(self, correlation_id: str | None = None) -> PipelineRun:
        """Execute stub pipeline — publishes completion event only."""
        cid = correlation_id or str(uuid4())
        run = PipelineRun(correlation_id=cid, status=PipelineStatus.RUNNING)
        logger.info("pipeline_started", correlation_id=cid)

        for stage in self.STAGES:
            if stage == "risk" and not self._risk_enabled:
                run.stage_results[stage] = StageResult(stage_name=stage, status="skipped")
                continue
            run.stage_results[stage] = StageResult(stage_name=stage, status="stub")

        run.status = PipelineStatus.COMPLETED
        run.completed_at = datetime.now(UTC)

        self._event_bus.publish(
            DomainEvent(
                event_type="pipeline.completed",
                correlation_id=cid,
                payload={"status": run.status, "stages": list(run.stage_results.keys())},
            )
        )
        logger.info("pipeline_completed", correlation_id=cid)
        return run
