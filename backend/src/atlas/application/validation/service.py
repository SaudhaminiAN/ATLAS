"""Trade validation application service."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog

from atlas.application.confluence.service import ConfluenceService
from atlas.application.market_context.service import MarketContextService
from atlas.application.market_data.service import MarketDataService
from atlas.application.mtf.service import MultiTimeframeAnalysisService
from atlas.application.news.service import NewsFilterService
from atlas.application.smc.service import SmartMoneyConceptsService
from atlas.application.strategy.service import StrategyEngineService
from atlas.application.technical.service import TechnicalAnalysisService
from atlas.domain.events.base import DomainEvent
from atlas.domain.models.enums import Timeframe
from atlas.domain.models.validation import ValidationContext, ValidationResult
from atlas.domain.ports.event_bus import EventBusProtocol
from atlas.domain.services.validation_rules import validate_context

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class TradeValidationConfig:
    """Trade validation settings from Spec 09."""

    primary_timeframe: Timeframe = Timeframe.M15


@dataclass
class TradeValidationService:
    """Apply deterministic pass/fail rules to confluence output."""

    market_data_service: MarketDataService
    confluence_service: ConfluenceService
    mtf_service: MultiTimeframeAnalysisService
    technical_analysis_service: TechnicalAnalysisService
    smc_service: SmartMoneyConceptsService
    market_context_service: MarketContextService
    news_filter: NewsFilterService
    strategy_engine: StrategyEngineService
    event_bus: EventBusProtocol
    config: TradeValidationConfig = field(default_factory=TradeValidationConfig)

    def validate(self, context: ValidationContext) -> ValidationResult:
        """Evaluate all enabled validation rules."""
        is_valid, rules = validate_context(context)
        failed_rules = tuple(
            result.rule_name for result in rules if result.enabled and not result.passed
        )

        return ValidationResult(
            instrument=context.confluence.instrument,
            direction=context.confluence.suggested_direction,
            is_valid=is_valid,
            rules=tuple(rules),
            failed_rules=failed_rules,
            strategy_profile_id=context.strategy.id,
            validated_at=context.trigger_bar.open_time,
        )

    async def validate_symbol(
        self,
        symbol: str,
        *,
        as_of: datetime | None = None,
        publish_event: bool = True,
    ) -> ValidationResult | None:
        """Run analysis pipeline inputs and validate confluence output."""
        strategy = await self.strategy_engine.get_active()
        if not strategy:
            logger.warning("validation_no_active_strategy", symbol=symbol)
            return None

        instrument = await self.market_data_service.get_instrument(symbol)
        if not instrument:
            return None

        bars = await self.market_data_service.get_recent_bars(
            instrument,
            self.config.primary_timeframe,
            limit=5,
            as_of=as_of,
        )
        if not bars:
            return None

        confluence = await self.confluence_service.calculate_symbol(
            symbol,
            as_of=as_of,
            publish_event=False,
        )
        if not confluence:
            return None

        mtf = await self.mtf_service.analyze_symbol(symbol, as_of=as_of, publish_event=False)
        context = await self.market_context_service.analyze_symbol(symbol, as_of=as_of)
        technical = await self.technical_analysis_service.analyze_symbol(
            symbol,
            timeframe=self.config.primary_timeframe,
            as_of=as_of,
            publish_event=False,
        )
        smc = await self.smc_service.analyze_symbol(
            symbol,
            timeframe=self.config.primary_timeframe,
            as_of=as_of,
            publish_event=False,
        )

        if not all([mtf, context, technical, smc]):
            return None

        news_status = self.news_filter.check(as_of or datetime.now(UTC))

        validation_context = ValidationContext(
            confluence=confluence,
            mtf=mtf,
            context=context,
            technical=technical,
            smc=smc,
            news=news_status,
            strategy=strategy,
            trigger_bar=bars[-1],
        )

        result = self.validate(validation_context)

        if publish_event:
            self._publish_completed(result)

        return result

    def _publish_completed(self, result: ValidationResult) -> None:
        self.event_bus.publish(
            DomainEvent(
                event_type="validation.completed",
                correlation_id=f"validation-{result.instrument.symbol}",
                payload={
                    "symbol": result.instrument.symbol,
                    "direction": result.direction.value,
                    "is_valid": result.is_valid,
                    "failed_rules": list(result.failed_rules),
                    "strategy_profile_id": result.strategy_profile_id,
                    "rules": [
                        {
                            "rule_name": rule.rule_name,
                            "passed": rule.passed,
                            "reason": rule.reason,
                            "enabled": rule.enabled,
                        }
                        for rule in result.rules
                    ],
                    "validated_at": result.validated_at.isoformat(),
                },
            )
        )
