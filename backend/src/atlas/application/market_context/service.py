"""Market context application service."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

import structlog

from atlas.application.market_data.service import MarketDataService
from atlas.domain.events.base import DomainEvent
from atlas.domain.models.enums import Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.market_context import MarketContext
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.ports.event_bus import EventBusProtocol
from atlas.domain.services.session_detection import detect_sessions
from atlas.domain.services.spread_assessment import assess_spread
from atlas.domain.services.structural_bias import compute_structural_bias
from atlas.domain.services.volatility_regime import classify_volatility_regime
from atlas.infrastructure.cache.context_cache import ContextCache

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class MarketContextConfig:
    """Market context settings from Spec 03."""

    bias_timeframe: Timeframe = Timeframe.H4
    primary_timeframe: Timeframe = Timeframe.M15
    atr_period: int = 14
    atr_percentile_lookback: int = 100
    min_bars_required: int = 100
    swing_lookback: int = 2
    spread_elevated_multiplier: Decimal = Decimal("1.5")
    spread_average_lookback: int = 20


@dataclass
class MarketContextService:
    """Compute and cache market context snapshots."""

    market_data_service: MarketDataService
    event_bus: EventBusProtocol
    context_cache: ContextCache
    config: MarketContextConfig = field(default_factory=MarketContextConfig)

    def compute(
        self,
        instrument: Instrument,
        primary_bars: list[OHLCVBar],
        bias_timeframe_bars: list[OHLCVBar],
        spread: Decimal | None = None,
        *,
        as_of: datetime | None = None,
    ) -> MarketContext:
        """Derive deterministic market context from bar history."""
        reference_time = as_of or (
            primary_bars[-1].open_time if primary_bars else datetime.now(UTC)
        )

        primary_session, active_sessions = detect_sessions(reference_time)

        if len(primary_bars) < self.config.min_bars_required:
            logger.warning(
                "market_context_insufficient_bars",
                symbol=instrument.symbol,
                count=len(primary_bars),
                required=self.config.min_bars_required,
            )

        regime, atr_value, atr_percentile = classify_volatility_regime(
            primary_bars,
            atr_period=self.config.atr_period,
            lookback=self.config.atr_percentile_lookback,
            min_bars_required=self.config.min_bars_required,
        )

        spread_status = assess_spread(
            spread,
            elevated_multiplier=self.config.spread_elevated_multiplier,
            average_lookback=self.config.spread_average_lookback,
        )

        structural_bias = compute_structural_bias(
            bias_timeframe_bars,
            swing_lookback=self.config.swing_lookback,
        )

        return MarketContext(
            instrument=instrument,
            primary_session=primary_session,
            active_sessions=active_sessions,
            volatility_regime=regime,
            spread_status=spread_status,
            structural_bias=structural_bias,
            atr_value=atr_value,
            atr_percentile=atr_percentile,
            computed_at=to_utc(reference_time),
        )

    async def analyze_symbol(
        self,
        symbol: str,
        *,
        as_of: datetime | None = None,
        publish_event: bool = True,
    ) -> MarketContext | None:
        """Fetch bars and compute context for a symbol."""
        instrument = await self.market_data_service.get_instrument(symbol)
        if not instrument:
            return None

        bar_limit = self.config.min_bars_required + self.config.atr_period + 5
        primary_bars = await self.market_data_service.get_recent_bars(
            instrument,
            self.config.primary_timeframe,
            limit=bar_limit,
            as_of=as_of,
        )
        bias_bars = await self.market_data_service.get_recent_bars(
            instrument,
            self.config.bias_timeframe,
            limit=bar_limit,
            as_of=as_of,
        )

        if not primary_bars:
            return None

        context = self.compute(
            instrument,
            primary_bars,
            bias_bars,
            as_of=as_of or primary_bars[-1].open_time,
        )
        await self.context_cache.set_latest(context)

        if publish_event:
            self._publish_updated(context)

        return context

    async def get_cached(self, symbol: str) -> MarketContext | None:
        """Return cached context if available."""
        cached = await self.context_cache.get_latest(symbol)
        if not cached:
            return None

        instrument = await self.market_data_service.get_instrument(symbol)
        if not instrument:
            return None

        from atlas.domain.models.enums import Bias, SpreadStatus, TradingSession, VolatilityRegime

        return MarketContext(
            instrument=instrument,
            primary_session=TradingSession(cached["primary_session"]),
            active_sessions=tuple(TradingSession(s) for s in cached["active_sessions"]),
            volatility_regime=VolatilityRegime(cached["volatility_regime"]),
            spread_status=SpreadStatus(cached["spread_status"]),
            structural_bias=Bias(cached["structural_bias"]),
            atr_value=Decimal(cached["atr_value"]),
            atr_percentile=Decimal(cached["atr_percentile"]),
            computed_at=datetime.fromisoformat(cached["computed_at"]),
        )

    def _publish_updated(self, context: MarketContext) -> None:
        self.event_bus.publish(
            DomainEvent(
                event_type="market_context.updated",
                correlation_id=f"context-{context.instrument.symbol}",
                payload={
                    "symbol": context.instrument.symbol,
                    "primary_session": context.primary_session.value,
                    "active_sessions": [s.value for s in context.active_sessions],
                    "volatility_regime": context.volatility_regime.value,
                    "spread_status": context.spread_status.value,
                    "structural_bias": context.structural_bias.value,
                    "atr_value": str(context.atr_value),
                    "atr_percentile": str(context.atr_percentile),
                    "computed_at": context.computed_at.isoformat(),
                },
            )
        )


def to_utc(dt: datetime) -> datetime:
    """Normalize to UTC."""
    from atlas.domain.services.bar_validation import to_utc as _to_utc

    return _to_utc(dt)
