"""Backtest REST endpoints (Spec 16)."""

from fastapi import APIRouter, Request

from atlas.domain.models.backtest import BacktestConfig, BacktestResult
from atlas.domain.models.enums import Timeframe
from atlas.presentation.api.dtos.backtest import (
    BacktestResultDTO,
    BacktestRunRequestDTO,
    DecisionSummaryDTO,
    ModuleAccuracySummaryDTO,
)
from atlas.presentation.api.schemas import ApiEnvelope, ApiError

router = APIRouter(prefix="/backtest", tags=["backtest"])


def _to_dto(result: BacktestResult) -> BacktestResultDTO:
    return BacktestResultDTO(
        symbol=result.symbol,
        timeframe=result.timeframe.value,
        start=result.start,
        end=result.end,
        bars_processed=result.bars_processed,
        pipeline_runs=result.pipeline_runs,
        completed_runs=result.completed_runs,
        skipped_runs=result.skipped_runs,
        failed_runs=result.failed_runs,
        decision_counts=[
            DecisionSummaryDTO(direction=item.direction.value, count=item.count)
            for item in result.decision_counts
        ],
        wait_reasons=list(result.wait_reasons),
        module_accuracy=[
            ModuleAccuracySummaryDTO(
                source=item.source,
                appearances=item.appearances,
                actionable_appearances=item.actionable_appearances,
            )
            for item in result.module_accuracy
        ],
        duration_ms=result.duration_ms,
    )


@router.post("/run", response_model=ApiEnvelope[BacktestResultDTO])
async def run_backtest(
    request: Request,
    body: BacktestRunRequestDTO,
) -> ApiEnvelope[BacktestResultDTO]:
    """Replay historical bars through the analysis pipeline."""
    try:
        timeframe = Timeframe(body.timeframe)
    except ValueError:
        return ApiEnvelope(
            success=False,
            error=ApiError(
                code="invalid_timeframe",
                message=f"Unknown timeframe: {body.timeframe}",
            ),
        )

    if body.end < body.start:
        return ApiEnvelope(
            success=False,
            error=ApiError(code="invalid_range", message="end must be >= start"),
        )

    config = BacktestConfig(
        symbol=body.symbol.upper(),
        timeframe=timeframe,
        start=body.start,
        end=body.end,
        persist_decisions=body.persist_decisions,
        persist_pipeline_runs=body.persist_pipeline_runs,
        risk_enabled=body.risk_enabled,
    )

    try:
        result = await request.app.state.container.backtest_runner.run(config)
    except ValueError as exc:
        return ApiEnvelope(
            success=False,
            error=ApiError(code="backtest_failed", message=str(exc)),
        )

    return ApiEnvelope(success=True, data=_to_dto(result))
