"""Analytics port (Spec 14)."""

from typing import Protocol

from atlas.domain.models.analytics import (
    AnalyticsFilters,
    DecisionStats,
    EquityPoint,
    ModuleAccuracy,
    PerformanceSummary,
)


class AnalyticsServiceProtocol(Protocol):
    """Compute performance and decision analytics."""

    async def get_performance_summary(self, filters: AnalyticsFilters) -> PerformanceSummary: ...

    async def get_decision_stats(self, filters: AnalyticsFilters) -> DecisionStats: ...

    async def get_module_accuracy(self, filters: AnalyticsFilters) -> list[ModuleAccuracy]: ...

    async def get_equity_curve(self, filters: AnalyticsFilters) -> list[EquityPoint]: ...
