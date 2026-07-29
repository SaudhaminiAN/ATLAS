"""Pipeline orchestrator stub tests."""

import pytest

from atlas.application.pipeline.orchestrator import AnalysisPipelineOrchestrator, PipelineStatus
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus


@pytest.mark.asyncio
async def test_pipeline_stub_completes_all_stages() -> None:
    """Stub pipeline marks all stages and completes."""
    bus = InMemoryEventBus()
    orchestrator = AnalysisPipelineOrchestrator(event_bus=bus, risk_enabled=False)
    run = await orchestrator.run(correlation_id="test-cid")

    assert run.status == PipelineStatus.COMPLETED
    assert run.correlation_id == "test-cid"
    assert "decision_engine" in run.stage_results
    assert run.stage_results["risk"].status == "skipped"


@pytest.mark.asyncio
async def test_pipeline_publishes_completion_event() -> None:
    """Pipeline publishes pipeline.completed event."""
    bus = InMemoryEventBus()
    events: list[str] = []
    bus.subscribe("pipeline.completed", lambda e: events.append(e.event_type))
    orchestrator = AnalysisPipelineOrchestrator(event_bus=bus)

    await orchestrator.run(correlation_id="evt-cid")

    assert events == ["pipeline.completed"]
