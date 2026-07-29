"""Analytics application service (Spec 14)."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from atlas.domain.models.analytics import (
    AnalyticsFilters,
    DecisionStats,
    EquityPoint,
    ModuleAccuracy,
    PerformanceSummary,
)
from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.journal import DecisionFilters
from atlas.domain.services.analytics_metrics import (
    compute_decision_stats,
    compute_module_accuracy,
    empty_performance_summary,
)
from atlas.infrastructure.persistence.repositories import DecisionRepository

ANALYTICS_QUERY_LIMIT = 10_000


@dataclass
class AnalyticsService:
    """Read decision history and compute analytics metrics."""

    session_factory: async_sessionmaker[AsyncSession]

    async def get_performance_summary(self, filters: AnalyticsFilters) -> PerformanceSummary:
        """Trade metrics — zeroed until execution engine (Spec 11) provides trades."""
        del filters
        return empty_performance_summary()

    async def get_decision_stats(self, filters: AnalyticsFilters) -> DecisionStats:
        decisions = await self._load_decisions(filters)
        return compute_decision_stats(decisions)

    async def get_module_accuracy(self, filters: AnalyticsFilters) -> list[ModuleAccuracy]:
        decisions = await self._load_decisions(filters)
        return compute_module_accuracy(decisions)

    async def get_equity_curve(self, filters: AnalyticsFilters) -> list[EquityPoint]:
        """Equity curve — empty until trades exist (Spec 11)."""
        del filters
        return []

    async def _load_decisions(self, filters: AnalyticsFilters) -> list[TradingDecision]:
        query_filters = DecisionFilters(
            symbol=filters.symbol,
            start=filters.start,
            end=filters.end,
            limit=ANALYTICS_QUERY_LIMIT,
            offset=0,
        )
        async with self.session_factory() as session:
            repo = DecisionRepository(session)
            decisions = await repo.query(query_filters)
            if filters.strategy_profile_id:
                decisions = [
                    d for d in decisions if d.strategy_id == filters.strategy_profile_id
                ]
        return decisions
