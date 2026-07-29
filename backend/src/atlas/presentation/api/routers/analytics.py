"""Analytics REST endpoints (Spec 14)."""

from datetime import datetime

from fastapi import APIRouter, Query, Request

from atlas.domain.models.analytics import (
    AnalyticsFilters,
    DecisionStats,
    EquityPoint,
    ModuleAccuracy,
    PerformanceSummary,
)
from atlas.presentation.api.dtos.analytics import (
    DecisionStatsDTO,
    EquityPointDTO,
    ModuleAccuracyDTO,
    PerformanceSummaryDTO,
    WaitReasonCountDTO,
)
from atlas.presentation.api.schemas import ApiEnvelope

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _filters(
    symbol: str | None,
    strategy_profile_id: str | None,
    start: datetime | None,
    end: datetime | None,
) -> AnalyticsFilters:
    return AnalyticsFilters(
        symbol=symbol,
        strategy_profile_id=strategy_profile_id,
        start=start,
        end=end,
    )


def _decision_stats_dto(stats: DecisionStats) -> DecisionStatsDTO:
    return DecisionStatsDTO(
        total_decisions=stats.total_decisions,
        wait_count=stats.wait_count,
        buy_count=stats.buy_count,
        sell_count=stats.sell_count,
        actionable_count=stats.actionable_count,
        wait_rate=stats.wait_rate,
        actionable_rate=stats.actionable_rate,
        top_wait_reasons=[
            WaitReasonCountDTO(reason=item.reason, count=item.count)
            for item in stats.top_wait_reasons
        ],
    )


def _module_accuracy_dto(item: ModuleAccuracy) -> ModuleAccuracyDTO:
    return ModuleAccuracyDTO(
        source=item.source,
        appearances=item.appearances,
        true_positive=item.true_positive,
        false_signal=item.false_signal,
        neutral_wait=item.neutral_wait,
        true_positive_rate=item.true_positive_rate,
        false_signal_rate=item.false_signal_rate,
    )


def _performance_dto(summary: PerformanceSummary) -> PerformanceSummaryDTO:
    return PerformanceSummaryDTO(
        total_trades=summary.total_trades,
        winning_trades=summary.winning_trades,
        losing_trades=summary.losing_trades,
        win_rate=summary.win_rate,
        profit_factor=summary.profit_factor,
        total_pnl=summary.total_pnl,
        max_drawdown=summary.max_drawdown,
    )


def _equity_point_dto(point: EquityPoint) -> EquityPointDTO:
    return EquityPointDTO(timestamp=point.timestamp, equity=point.equity)


@router.get("/decision-stats")
async def get_decision_stats(
    request: Request,
    symbol: str | None = Query(default=None),
    strategy_profile_id: str | None = Query(default=None),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
) -> ApiEnvelope[DecisionStatsDTO]:
    """Decision counts, WAIT rate, and top WAIT reasons."""
    service = request.app.state.container.analytics_service
    stats = await service.get_decision_stats(
        _filters(symbol, strategy_profile_id, start, end)
    )
    return ApiEnvelope(success=True, data=_decision_stats_dto(stats))


@router.get("/module-accuracy")
async def get_module_accuracy(
    request: Request,
    symbol: str | None = Query(default=None),
    strategy_profile_id: str | None = Query(default=None),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
) -> ApiEnvelope[list[ModuleAccuracyDTO]]:
    """Per-evidence-source accuracy metrics."""
    service = request.app.state.container.analytics_service
    items = await service.get_module_accuracy(
        _filters(symbol, strategy_profile_id, start, end)
    )
    return ApiEnvelope(success=True, data=[_module_accuracy_dto(item) for item in items])


@router.get("/performance")
async def get_performance_summary(
    request: Request,
    symbol: str | None = Query(default=None),
    strategy_profile_id: str | None = Query(default=None),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
) -> ApiEnvelope[PerformanceSummaryDTO]:
    """Trade performance summary (zeroed until paper trading in Spec 11)."""
    service = request.app.state.container.analytics_service
    summary = await service.get_performance_summary(
        _filters(symbol, strategy_profile_id, start, end)
    )
    return ApiEnvelope(success=True, data=_performance_dto(summary))


@router.get("/equity-curve")
async def get_equity_curve(
    request: Request,
    symbol: str | None = Query(default=None),
    strategy_profile_id: str | None = Query(default=None),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
) -> ApiEnvelope[list[EquityPointDTO]]:
    """Equity curve points (empty until trades exist)."""
    service = request.app.state.container.analytics_service
    points = await service.get_equity_curve(_filters(symbol, strategy_profile_id, start, end))
    return ApiEnvelope(success=True, data=[_equity_point_dto(p) for p in points])
