"""Confluence application service."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog

from atlas.application.market_context.service import MarketContextService
from atlas.application.mtf.service import MultiTimeframeAnalysisService
from atlas.application.news.service import NewsFilterService
from atlas.application.price_action.service import PriceActionService
from atlas.application.smc.service import SmartMoneyConceptsService
from atlas.application.strategy.service import StrategyEngineService
from atlas.application.technical.service import TechnicalAnalysisService
from atlas.domain.events.base import DomainEvent
from atlas.domain.models.confluence import ConfluenceResult
from atlas.domain.models.enums import Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.market_context import MarketContext
from atlas.domain.models.mtf import MTFAnalysis
from atlas.domain.models.news import NewsFilterStatus
from atlas.domain.models.price_action import PriceActionResult
from atlas.domain.models.smc import SMCAnalysisResult
from atlas.domain.models.strategy import StrategyProfile
from atlas.domain.models.technical import TechnicalAnalysisResult
from atlas.domain.ports.event_bus import EventBusProtocol
from atlas.domain.services.confluence_scoring import calculate_confluence

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ConfluenceConfig:
    """Confluence settings from Spec 08."""

    min_evidence_count: int = 3
    primary_timeframe: Timeframe = Timeframe.M15


@dataclass
class ConfluenceService:
    """Aggregate weighted evidence from all analysis modules."""

    market_context_service: MarketContextService
    mtf_service: MultiTimeframeAnalysisService
    technical_analysis_service: TechnicalAnalysisService
    smc_service: SmartMoneyConceptsService
    price_action_service: PriceActionService
    news_filter: NewsFilterService
    strategy_engine: StrategyEngineService
    event_bus: EventBusProtocol
    config: ConfluenceConfig = field(default_factory=ConfluenceConfig)

    def calculate(
        self,
        instrument: Instrument,
        mtf: MTFAnalysis,
        technical: TechnicalAnalysisResult,
        smc: SMCAnalysisResult,
        price_action: PriceActionResult,
        context: MarketContext,
        news_status: NewsFilterStatus,
        strategy: StrategyProfile,
        *,
        computed_at: datetime | None = None,
    ) -> ConfluenceResult:
        """Calculate confluence from pre-computed module outputs."""
        return calculate_confluence(
            instrument,
            mtf,
            technical,
            smc,
            price_action,
            context,
            news_status,
            strategy,
            min_evidence_count=self.config.min_evidence_count,
            computed_at=computed_at,
        )

    async def calculate_symbol(
        self,
        symbol: str,
        *,
        as_of: datetime | None = None,
        publish_event: bool = True,
    ) -> ConfluenceResult | None:
        """Run all analysis modules and calculate confluence for a symbol."""
        strategy = await self.strategy_engine.get_active()
        if not strategy:
            logger.warning("confluence_no_active_strategy", symbol=symbol)
            return None

        context = await self.market_context_service.analyze_symbol(symbol, as_of=as_of)
        if not context:
            return None

        mtf = await self.mtf_service.analyze_symbol(symbol, as_of=as_of, publish_event=False)
        if not mtf:
            return None

        technical = await self.technical_analysis_service.analyze_symbol(
            symbol,
            timeframe=self.config.primary_timeframe,
            as_of=as_of,
            publish_event=False,
        )
        if not technical:
            return None

        smc = await self.smc_service.analyze_symbol(
            symbol,
            timeframe=self.config.primary_timeframe,
            as_of=as_of,
            publish_event=False,
        )
        if not smc:
            return None

        price_action = await self.price_action_service.analyze_symbol(
            symbol,
            timeframe=self.config.primary_timeframe,
            as_of=as_of,
            publish_event=False,
        )
        if not price_action:
            return None

        news_status = self.news_filter.check(as_of or datetime.now(UTC))

        result = self.calculate(
            context.instrument,
            mtf,
            technical,
            smc,
            price_action,
            context,
            news_status,
            strategy,
            computed_at=as_of or context.computed_at,
        )

        if publish_event:
            self._publish_calculated(result)

        return result

    def _publish_calculated(self, result: ConfluenceResult) -> None:
        self.event_bus.publish(
            DomainEvent(
                event_type="confluence.calculated",
                correlation_id=f"confluence-{result.instrument.symbol}",
                payload={
                    "symbol": result.instrument.symbol,
                    "suggested_direction": result.suggested_direction.value,
                    "total_score": str(result.total_score),
                    "raw_score": str(result.raw_score),
                    "bullish_raw": str(result.bullish_raw),
                    "bearish_raw": str(result.bearish_raw),
                    "news_penalty": str(result.news_penalty),
                    "evidence_count": result.evidence_count,
                    "has_conflict": result.has_conflict,
                    "strategy_profile_id": result.strategy_profile_id,
                    "module_scores": [
                        {
                            "source": module.source,
                            "direction": module.direction.value,
                            "score": str(module.score),
                            "weight": str(module.weight),
                            "weighted_contribution": str(module.weighted_contribution),
                        }
                        for module in result.module_scores
                    ],
                    "computed_at": result.computed_at.isoformat(),
                },
            )
        )
