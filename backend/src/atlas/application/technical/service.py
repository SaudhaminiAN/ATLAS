"""Technical analysis application service."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

import structlog

from atlas.application.market_data.service import MarketDataService
from atlas.domain.events.base import DomainEvent
from atlas.domain.models.enums import Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.technical import TechnicalAnalysisResult
from atlas.domain.ports.event_bus import EventBusProtocol
from atlas.domain.services.indicators import build_indicator_context
from atlas.domain.services.support_resistance import build_key_levels, nearest_levels
from atlas.domain.services.swing_points import detect_swings
from atlas.domain.services.technical_scoring import compute_context_scores
from atlas.domain.services.trend_classification import classify_trend

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class TechnicalAnalysisConfig:
    """Technical analysis settings from Spec 05."""

    swing_lookback: int = 2
    merge_tolerance_pct: Decimal = Decimal("0.001")
    min_bars: int = 200
    bar_lookback: int = 250


@dataclass
class TechnicalAnalysisService:
    """Provide structural technical context from OHLCV history."""

    market_data_service: MarketDataService
    event_bus: EventBusProtocol
    config: TechnicalAnalysisConfig = field(default_factory=TechnicalAnalysisConfig)

    def analyze(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        bars: list[OHLCVBar],
        *,
        computed_at: datetime | None = None,
    ) -> TechnicalAnalysisResult:
        """Run deterministic technical analysis."""
        if len(bars) < self.config.min_bars:
            logger.warning(
                "technical_insufficient_bars",
                symbol=instrument.symbol,
                timeframe=timeframe.value,
                count=len(bars),
                required=self.config.min_bars,
            )

        swings = detect_swings(bars, lookback=self.config.swing_lookback)
        trend = classify_trend(bars, swing_lookback=self.config.swing_lookback)
        key_levels = build_key_levels(swings, merge_tolerance_pct=self.config.merge_tolerance_pct)

        close = bars[-1].close if bars else Decimal(0)
        nearest_support, nearest_resistance = nearest_levels(close, key_levels)

        indicator_context = build_indicator_context(bars) if bars else {}
        ema20 = indicator_context.get("ema20")
        ema50 = indicator_context.get("ema50")
        rsi = indicator_context.get("rsi14")

        bullish_score, bearish_score = compute_context_scores(
            trend,
            close,
            ema20,
            ema50,
            rsi,
        )

        return TechnicalAnalysisResult(
            instrument=instrument,
            timeframe=timeframe,
            trend=trend,
            key_levels=tuple(key_levels),
            nearest_support=nearest_support,
            nearest_resistance=nearest_resistance,
            indicator_context=indicator_context,
            bullish_context_score=bullish_score,
            bearish_context_score=bearish_score,
            computed_at=computed_at or datetime.now(UTC),
        )

    async def analyze_symbol(
        self,
        symbol: str,
        timeframe: Timeframe = Timeframe.M15,
        *,
        as_of: datetime | None = None,
        publish_event: bool = True,
    ) -> TechnicalAnalysisResult | None:
        """Fetch bars and analyze for a symbol/timeframe."""
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

        result = self.analyze(
            instrument,
            timeframe,
            bars,
            computed_at=as_of or bars[-1].open_time,
        )

        if publish_event:
            self._publish_completed(result)

        return result

    def _publish_completed(self, result: TechnicalAnalysisResult) -> None:
        self.event_bus.publish(
            DomainEvent(
                event_type="analysis.technical.completed",
                correlation_id=f"technical-{result.instrument.symbol}-{result.timeframe.value}",
                payload={
                    "symbol": result.instrument.symbol,
                    "timeframe": result.timeframe.value,
                    "trend": result.trend.value,
                    "bullish_context_score": str(result.bullish_context_score),
                    "bearish_context_score": str(result.bearish_context_score),
                    "nearest_support": (
                        str(result.nearest_support) if result.nearest_support else None
                    ),
                    "nearest_resistance": (
                        str(result.nearest_resistance) if result.nearest_resistance else None
                    ),
                    "key_level_count": len(result.key_levels),
                    "computed_at": result.computed_at.isoformat(),
                },
            )
        )
