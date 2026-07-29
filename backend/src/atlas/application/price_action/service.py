"""Price action application service."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

import structlog

from atlas.application.market_data.service import MarketDataService
from atlas.application.smc.service import SmartMoneyConceptsService
from atlas.application.technical.service import TechnicalAnalysisService
from atlas.domain.events.base import DomainEvent
from atlas.domain.models.enums import Bias, Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.price_action import CandlePattern, PriceActionResult
from atlas.domain.models.price_level import PriceLevel
from atlas.domain.models.smc import SMCAnalysisResult
from atlas.domain.ports.event_bus import EventBusProtocol
from atlas.domain.services.candle_patterns import detect_patterns_on_closed_bar
from atlas.domain.services.key_level_proximity import apply_proximity_scoring

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class PriceActionConfig:
    """Price action settings from Spec 07."""

    level_proximity_pct: Decimal = Decimal("0.0015")
    min_pattern_strength: Decimal = Decimal("0.30")
    displacement_atr_multiplier: Decimal = Decimal("1.5")
    min_bars: int = 3
    bar_lookback: int = 120


def _empty_result(
    instrument: Instrument,
    timeframe: Timeframe,
    computed_at: datetime | None = None,
) -> PriceActionResult:
    return PriceActionResult(
        instrument=instrument,
        timeframe=timeframe,
        patterns=(),
        strongest_pattern=None,
        computed_at=computed_at or datetime.now(UTC),
    )


def _strongest_pattern(patterns: list[CandlePattern]) -> CandlePattern | None:
    if not patterns:
        return None
    return max(patterns, key=lambda pattern: pattern.strength)


@dataclass
class PriceActionService:
    """Detect candlestick patterns and score them at key levels."""

    market_data_service: MarketDataService
    technical_analysis_service: TechnicalAnalysisService
    smc_service: SmartMoneyConceptsService
    event_bus: EventBusProtocol
    config: PriceActionConfig = field(default_factory=PriceActionConfig)

    def analyze(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        bars: list[OHLCVBar],
        key_levels: list[PriceLevel],
        smc: SMCAnalysisResult,
        *,
        computed_at: datetime | None = None,
    ) -> PriceActionResult:
        """Run deterministic price action analysis."""
        if len(bars) < self.config.min_bars:
            logger.warning(
                "price_action_insufficient_bars",
                symbol=instrument.symbol,
                timeframe=timeframe.value,
                count=len(bars),
            )
            return _empty_result(instrument, timeframe, computed_at)

        raw_patterns = detect_patterns_on_closed_bar(
            bars,
            displacement_atr_multiplier=self.config.displacement_atr_multiplier,
        )
        patterns = apply_proximity_scoring(
            raw_patterns,
            bars,
            key_levels,
            smc,
            proximity_pct=self.config.level_proximity_pct,
            min_pattern_strength=self.config.min_pattern_strength,
        )
        patterns = [pattern for pattern in patterns if pattern.direction != Bias.NEUTRAL]

        return PriceActionResult(
            instrument=instrument,
            timeframe=timeframe,
            patterns=tuple(patterns),
            strongest_pattern=_strongest_pattern(patterns),
            computed_at=computed_at or datetime.now(UTC),
        )

    async def analyze_symbol(
        self,
        symbol: str,
        timeframe: Timeframe = Timeframe.M15,
        *,
        as_of: datetime | None = None,
        publish_event: bool = True,
    ) -> PriceActionResult | None:
        """Fetch inputs and analyze price action for a symbol/timeframe."""
        instrument = await self.market_data_service.get_instrument(symbol)
        if not instrument:
            return None

        bars = await self.market_data_service.get_recent_bars(
            instrument,
            timeframe,
            limit=self.config.bar_lookback,
            as_of=as_of,
        )
        if not bars:
            return None

        technical = self.technical_analysis_service.analyze(
            instrument,
            timeframe,
            bars,
            computed_at=as_of or bars[-1].open_time,
        )
        smc = self.smc_service.analyze(
            instrument,
            timeframe,
            bars,
            computed_at=as_of or bars[-1].open_time,
        )

        result = self.analyze(
            instrument,
            timeframe,
            bars,
            list(technical.key_levels),
            smc,
            computed_at=as_of or bars[-1].open_time,
        )

        if publish_event:
            self._publish_completed(result)

        return result

    def _publish_completed(self, result: PriceActionResult) -> None:
        strongest = result.strongest_pattern
        self.event_bus.publish(
            DomainEvent(
                event_type="analysis.price_action.completed",
                correlation_id=(
                    f"price-action-{result.instrument.symbol}-{result.timeframe.value}"
                ),
                payload={
                    "symbol": result.instrument.symbol,
                    "timeframe": result.timeframe.value,
                    "pattern_count": len(result.patterns),
                    "strongest_pattern": strongest.pattern_type if strongest else None,
                    "strongest_direction": strongest.direction.value if strongest else None,
                    "strongest_strength": str(strongest.strength) if strongest else None,
                    "at_key_level": strongest.at_key_level if strongest else False,
                    "computed_at": result.computed_at.isoformat(),
                },
            )
        )
