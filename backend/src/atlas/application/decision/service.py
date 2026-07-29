"""Decision engine service (Spec 17)."""

from dataclasses import dataclass
from uuid import uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from atlas.domain.events.base import DomainEvent
from atlas.domain.models.confluence import ConfluenceResult
from atlas.domain.models.decision import TradingDecision, wait_decision
from atlas.domain.models.enums import Direction
from atlas.domain.models.news import NewsFilterStatus
from atlas.domain.models.strategy import StrategyProfile
from atlas.domain.models.validation import ValidationResult
from atlas.domain.ports.event_bus import EventBusProtocol
from atlas.infrastructure.cache.decision_cache import DecisionCache
from atlas.infrastructure.persistence.decision_serializers import decision_to_cache_dict
from atlas.infrastructure.persistence.repositories import DecisionRepository

logger = structlog.get_logger(__name__)


@dataclass
class DecisionEngineService:
    """Resolve final BUY / SELL / WAIT and persist every decision."""

    event_bus: EventBusProtocol
    session_factory: async_sessionmaker[AsyncSession] | None = None
    decision_cache: DecisionCache | None = None

    def resolve(
        self,
        confluence: ConfluenceResult,
        validation: ValidationResult,
        news_status: NewsFilterStatus,
        strategy: StrategyProfile,
        *,
        correlation_id: str,
        risk_within_limits: bool | None = None,
    ) -> TradingDecision:
        """Apply deterministic decision priority rules (no side effects)."""
        common = {
            "correlation_id": correlation_id,
            "strategy_id": strategy.id,
            "confluence_score": confluence.total_score,
            "confluence": confluence,
            "validation": validation,
            "news_status": news_status,
            "decided_at": confluence.computed_at,
        }
        if news_status.is_blocked:
            return wait_decision(
                confluence.instrument,
                "High-impact news window active",
                **common,
            )
        if not validation.is_valid:
            return wait_decision(
                confluence.instrument,
                f"Validation failed: {', '.join(validation.failed_rules)}",
                **common,
            )
        if confluence.total_score < strategy.min_confluence_score:
            return wait_decision(
                confluence.instrument,
                "Confluence below threshold",
                **common,
            )
        if not strategy.is_direction_enabled(confluence.suggested_direction):
            return wait_decision(
                confluence.instrument,
                "Direction disabled by strategy profile",
                **common,
            )
        if risk_within_limits is False:
            return wait_decision(
                confluence.instrument,
                "Risk limits breached",
                **common,
            )
        if confluence.suggested_direction == Direction.WAIT:
            return wait_decision(
                confluence.instrument,
                "Insufficient evidence",
                **common,
            )
        return TradingDecision(
            id=uuid4(),
            instrument=confluence.instrument,
            direction=confluence.suggested_direction,
            is_actionable=True,
            confluence_score=confluence.total_score,
            strategy_id=strategy.id,
            reason="Confluence and validation passed",
            correlation_id=correlation_id,
            decided_at=confluence.computed_at,
            confluence_snapshot=confluence,
            validation_snapshot=validation,
            news_status=news_status,
        )

    async def emit(
        self,
        decision: TradingDecision,
        *,
        persist: bool = True,
        publish: bool = True,
    ) -> None:
        """Publish event, optionally persist to DB and update cache."""
        if publish:
            self._publish_decision(decision)
        if not persist:
            return
        try:
            if self.session_factory is not None:
                async with self.session_factory() as session:
                    await DecisionRepository(session).insert_idempotent(decision)
            if self.decision_cache is not None:
                await self.decision_cache.set_latest(decision)
        except Exception:
            logger.exception("decision_persist_failed", decision_id=str(decision.id))

    async def get_latest(self, symbol: str) -> TradingDecision | None:
        """Return latest decision from cache or database."""
        if self.decision_cache is not None:
            cached = await self.decision_cache.get_latest(symbol)
            if cached is not None:
                return cached
        if self.session_factory is None:
            return None
        async with self.session_factory() as session:
            return await DecisionRepository(session).get_latest(symbol)

    async def get_history(
        self,
        symbol: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TradingDecision]:
        """Return paginated decision history."""
        if self.session_factory is None:
            return []
        async with self.session_factory() as session:
            return await DecisionRepository(session).list_history(
                symbol,
                limit=limit,
                offset=offset,
            )

    def _publish_decision(self, decision: TradingDecision) -> None:
        self.event_bus.publish(
            DomainEvent(
                event_type="decision.emitted",
                correlation_id=decision.correlation_id,
                payload={
                    "id": str(decision.id),
                    "symbol": decision.instrument.symbol,
                    "direction": decision.direction.value,
                    "is_actionable": decision.is_actionable,
                    "confluence_score": str(decision.confluence_score),
                    "reason": decision.reason,
                    "strategy_id": decision.strategy_id,
                    "decided_at": decision.decided_at.isoformat(),
                    "decision_snapshot": decision_to_cache_dict(decision),
                },
            )
        )
