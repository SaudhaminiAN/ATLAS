"""Multi-timeframe analysis application service."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

import structlog

from atlas.application.market_data.service import MarketDataService
from atlas.application.strategy.service import StrategyEngineService
from atlas.domain.events.base import DomainEvent
from atlas.domain.models.enums import Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.mtf import MTFAnalysis
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.smc import SMCAnalysisResult
from atlas.domain.models.strategy import StrategyProfile
from atlas.domain.models.technical import TechnicalAnalysisResult
from atlas.domain.ports.event_bus import EventBusProtocol
from atlas.domain.services.mtf_alignment import compute_alignment, detect_conflicts
from atlas.domain.services.mtf_bias import compute_timeframe_bias

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class MTFConfig:
    """MTF analysis settings from Spec 04."""

    alignment_threshold: Decimal = Decimal("0.75")
    bias_source: str = "smc_trend"
    swing_lookback: int = 2
    min_bars: int = 50
    bar_lookback: int = 120


@dataclass
class MultiTimeframeAnalysisService:
    """Align directional bias across multiple timeframes."""

    market_data_service: MarketDataService
    strategy_engine: StrategyEngineService
    event_bus: EventBusProtocol
    config: MTFConfig = field(default_factory=MTFConfig)

    def analyze(
        self,
        instrument: Instrument,
        timeframe_bars: dict[Timeframe, list[OHLCVBar]],
        smc_results: dict[Timeframe, SMCAnalysisResult | None],
        technical_results: dict[Timeframe, TechnicalAnalysisResult | None],
        strategy: StrategyProfile,
        *,
        computed_at: datetime | None = None,
    ) -> MTFAnalysis:
        """Compute MTF alignment from per-TF inputs."""
        active_timeframes = list(strategy.active_timeframes)
        biases = []

        for timeframe in active_timeframes:
            bars = timeframe_bars.get(timeframe, [])
            smc = smc_results.get(timeframe)
            technical = technical_results.get(timeframe)
            if len(bars) < self.config.min_bars:
                logger.warning(
                    "mtf_insufficient_bars",
                    symbol=instrument.symbol,
                    timeframe=timeframe.value,
                    count=len(bars),
                )
            biases.append(
                compute_timeframe_bias(
                    timeframe,
                    bars,
                    smc,
                    technical,
                    bias_source=self.config.bias_source,
                    swing_lookback=self.config.swing_lookback,
                    min_bars=self.config.min_bars,
                )
            )

        alignment_score, dominant_bias, aligned = compute_alignment(
            biases,
            self.config.alignment_threshold,
        )
        has_conflict, distant_conflict = detect_conflicts(biases, active_timeframes)

        result = MTFAnalysis(
            instrument=instrument,
            biases=tuple(biases),
            alignment_score=alignment_score,
            dominant_bias=dominant_bias,
            has_conflict=has_conflict,
            distant_conflict=distant_conflict,
            aligned=aligned,
            computed_at=computed_at or datetime.now(UTC),
        )
        return result

    async def analyze_symbol(
        self,
        symbol: str,
        *,
        as_of: datetime | None = None,
        smc_results: dict[Timeframe, SMCAnalysisResult | None] | None = None,
        technical_results: dict[Timeframe, TechnicalAnalysisResult | None] | None = None,
        publish_event: bool = True,
    ) -> MTFAnalysis | None:
        """Fetch bars and run MTF analysis for a symbol."""
        instrument = await self.market_data_service.get_instrument(symbol)
        if not instrument:
            return None

        strategy = await self.strategy_engine.get_active()
        timeframe_bars: dict[Timeframe, list[OHLCVBar]] = {}

        for timeframe in strategy.active_timeframes:
            bars = await self.market_data_service.get_recent_bars(
                instrument,
                timeframe,
                limit=self.config.bar_lookback,
                as_of=as_of,
            )
            timeframe_bars[timeframe] = bars

        smc_map = smc_results or {}
        technical_map = technical_results or {}

        result = self.analyze(
            instrument,
            timeframe_bars,
            smc_map,
            technical_map,
            strategy,
            computed_at=as_of,
        )

        if publish_event:
            self._publish_completed(result)

        return result

    def _publish_completed(self, analysis: MTFAnalysis) -> None:
        self.event_bus.publish(
            DomainEvent(
                event_type="analysis.mtf.completed",
                correlation_id=f"mtf-{analysis.instrument.symbol}",
                payload={
                    "symbol": analysis.instrument.symbol,
                    "alignment_score": str(analysis.alignment_score),
                    "dominant_bias": analysis.dominant_bias.value,
                    "has_conflict": analysis.has_conflict,
                    "distant_conflict": analysis.distant_conflict,
                    "aligned": analysis.aligned,
                    "biases": [
                        {
                            "timeframe": b.timeframe.value,
                            "bias": b.bias.value,
                            "confidence": str(b.confidence),
                            "trend_source": b.trend_source,
                        }
                        for b in analysis.biases
                    ],
                    "computed_at": analysis.computed_at.isoformat(),
                },
            )
        )
