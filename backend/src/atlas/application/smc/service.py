"""Smart money concepts application service."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

import structlog

from atlas.application.market_data.service import MarketDataService
from atlas.domain.events.base import DomainEvent
from atlas.domain.models.enums import Bias, Timeframe, Trend
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.smc import SMCAnalysisResult
from atlas.domain.ports.event_bus import EventBusProtocol
from atlas.domain.services.fair_value_gaps import detect_fair_value_gaps
from atlas.domain.services.liquidity_pools import detect_liquidity_pools
from atlas.domain.services.order_blocks import detect_order_blocks
from atlas.domain.services.smc_structure import detect_structure_breaks, directional_bias_from_smc
from atlas.domain.services.trend_classification import classify_trend

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SMCConfig:
    """SMC settings from Spec 06."""

    swing_lookback: int = 2
    displacement_atr_multiplier: Decimal = Decimal("1.5")
    ob_mitigation_pct: Decimal = Decimal("0.50")
    equal_level_tolerance_pct: Decimal = Decimal("0.001")
    fvg_fill_pct: Decimal = Decimal("0.50")
    min_bars: int = 50
    bar_lookback: int = 120


def _neutral_result(
    instrument: Instrument,
    timeframe: Timeframe,
    computed_at: datetime | None = None,
) -> SMCAnalysisResult:
    return SMCAnalysisResult(
        instrument=instrument,
        timeframe=timeframe,
        trend=Trend.RANGING,
        last_bos=None,
        last_choch=None,
        order_blocks=(),
        liquidity_pools=(),
        fair_value_gaps=(),
        directional_bias=Bias.NEUTRAL,
        computed_at=computed_at or datetime.now(UTC),
    )


@dataclass
class SmartMoneyConceptsService:
    """Detect institutional-style market structure."""

    market_data_service: MarketDataService
    event_bus: EventBusProtocol
    config: SMCConfig = field(default_factory=SMCConfig)

    def analyze(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        bars: list[OHLCVBar],
        *,
        computed_at: datetime | None = None,
    ) -> SMCAnalysisResult:
        """Run deterministic SMC analysis."""
        if len(bars) < self.config.min_bars:
            logger.warning(
                "smc_insufficient_bars",
                symbol=instrument.symbol,
                timeframe=timeframe.value,
                count=len(bars),
            )
            return _neutral_result(instrument, timeframe, computed_at)

        trend = classify_trend(bars, self.config.swing_lookback)
        last_bos, last_choch = detect_structure_breaks(bars, self.config.swing_lookback)
        order_blocks = detect_order_blocks(
            bars,
            displacement_atr_multiplier=self.config.displacement_atr_multiplier,
            ob_mitigation_pct=self.config.ob_mitigation_pct,
        )
        liquidity_pools = detect_liquidity_pools(
            bars,
            swing_lookback=self.config.swing_lookback,
            equal_level_tolerance_pct=self.config.equal_level_tolerance_pct,
        )
        fair_value_gaps = detect_fair_value_gaps(bars, fvg_fill_pct=self.config.fvg_fill_pct)
        bias = directional_bias_from_smc(trend, last_bos, last_choch)

        return SMCAnalysisResult(
            instrument=instrument,
            timeframe=timeframe,
            trend=trend,
            last_bos=last_bos,
            last_choch=last_choch,
            order_blocks=tuple(order_blocks),
            liquidity_pools=tuple(liquidity_pools),
            fair_value_gaps=tuple(fair_value_gaps),
            directional_bias=bias,
            computed_at=computed_at or datetime.now(UTC),
        )

    async def analyze_symbol(
        self,
        symbol: str,
        timeframe: Timeframe = Timeframe.M15,
        *,
        as_of: datetime | None = None,
        publish_event: bool = True,
    ) -> SMCAnalysisResult | None:
        """Fetch bars and analyze SMC for a symbol/timeframe."""
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

    def _publish_completed(self, result: SMCAnalysisResult) -> None:
        self.event_bus.publish(
            DomainEvent(
                event_type="analysis.smc.completed",
                correlation_id=f"smc-{result.instrument.symbol}-{result.timeframe.value}",
                payload={
                    "symbol": result.instrument.symbol,
                    "timeframe": result.timeframe.value,
                    "trend": result.trend.value,
                    "directional_bias": result.directional_bias.value,
                    "order_block_count": len(result.order_blocks),
                    "liquidity_pool_count": len(result.liquidity_pools),
                    "fvg_count": len(result.fair_value_gaps),
                    "has_bos": result.last_bos is not None,
                    "has_choch": result.last_choch is not None,
                    "computed_at": result.computed_at.isoformat(),
                },
            )
        )
