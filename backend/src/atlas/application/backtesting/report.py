"""Build backtest report from pipeline runs (Spec 16)."""

from collections import Counter

from atlas.domain.models.backtest import (
    BacktestConfig,
    BacktestResult,
    DecisionSummary,
    ModuleAccuracySummary,
)
from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.enums import Direction
from atlas.domain.models.pipeline import PipelineRun, PipelineStatus


def build_backtest_result(
    runs: list[PipelineRun],
    config: BacktestConfig,
    decisions: list[TradingDecision],
    *,
    duration_ms: int,
) -> BacktestResult:
    """Aggregate pipeline runs and decisions into a backtest report."""
    direction_counts: Counter[Direction] = Counter()
    wait_reasons: Counter[str] = Counter()
    module_appearances: Counter[str] = Counter()
    module_actionable: Counter[str] = Counter()

    for decision in decisions:
        direction_counts[decision.direction] += 1
        if decision.direction == Direction.WAIT:
            wait_reasons[decision.reason] += 1
        snapshot = decision.confluence_snapshot
        if snapshot is None:
            continue
        for item in snapshot.evidence:
            module_appearances[item.source] += 1
            if decision.is_actionable:
                module_actionable[item.source] += 1

    completed = sum(1 for r in runs if r.status == PipelineStatus.COMPLETED)
    skipped = sum(1 for r in runs if r.status == PipelineStatus.SKIPPED)
    failed = sum(1 for r in runs if r.status == PipelineStatus.FAILED)

    decision_counts = tuple(
        DecisionSummary(direction=direction, count=count)
        for direction, count in sorted(direction_counts.items(), key=lambda x: x[0].value)
    )
    wait_reason_tuples = tuple(
        sorted(wait_reasons.items(), key=lambda x: (-x[1], x[0]))
    )
    module_accuracy = tuple(
        ModuleAccuracySummary(
            source=source,
            appearances=module_appearances[source],
            actionable_appearances=module_actionable[source],
        )
        for source in sorted(module_appearances)
    )

    return BacktestResult(
        symbol=config.symbol,
        timeframe=config.timeframe,
        start=config.start,
        end=config.end,
        bars_processed=len(runs),
        pipeline_runs=len(runs),
        completed_runs=completed,
        skipped_runs=skipped,
        failed_runs=failed,
        decision_counts=decision_counts,
        wait_reasons=wait_reason_tuples,
        module_accuracy=module_accuracy,
        duration_ms=duration_ms,
    )
