"""Market data ingestion and query service."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from atlas.domain.events.base import DomainEvent
from atlas.domain.models.enums import Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import (
    GapRecord,
    IngestResult,
    IngestStatus,
    OHLCVBar,
)
from atlas.domain.ports.event_bus import EventBusProtocol
from atlas.domain.services.bar_validation import (
    TIMEFRAME_MINUTES,
    compute_atr,
    expected_next_open_time,
    is_aligned_open_time,
    is_outlier_bar,
    to_utc,
    validate_ohlc_integrity,
    validate_positive_prices,
)
from atlas.infrastructure.cache.bar_cache import BarCache
from atlas.infrastructure.persistence.repositories import (
    InstrumentRepository,
    OHLCVBarRepository,
    bar_to_domain,
)

logger = structlog.get_logger(__name__)


@dataclass
class MarketDataConfig:
    """Market data settings from Spec 02."""

    outlier_atr_multiplier: Decimal = Decimal("5.0")
    outlier_atr_lookback: int = 14
    gap_tolerance_bars: int = 1


@dataclass
class MarketDataService:
    """Ingest, validate, persist, and query OHLCV bars."""

    session_factory: async_sessionmaker[AsyncSession]
    event_bus: EventBusProtocol
    bar_cache: BarCache
    config: MarketDataConfig = field(default_factory=MarketDataConfig)

    async def ingest_bar(self, bar: OHLCVBar, *, is_closed: bool = True) -> IngestResult:
        """Validate and persist a bar; publish events on closed bar acceptance."""
        if not is_closed:
            return IngestResult(
                status=IngestStatus.REJECTED,
                reason="Forming bar not accepted",
                rule="closed_bar_only",
            )

        open_time = to_utc(bar.open_time)
        normalized = OHLCVBar(
            instrument=bar.instrument,
            timeframe=bar.timeframe,
            open_time=open_time,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
            is_outlier=bar.is_outlier,
            quality_flags=list(bar.quality_flags),
        )

        if err := validate_ohlc_integrity(normalized):
            logger.warning("bar_rejected", rule="ohlc_integrity", reason=err, open_time=open_time)
            return IngestResult(status=IngestStatus.REJECTED, reason=err, rule="ohlc_integrity")

        if err := validate_positive_prices(normalized):
            logger.warning("bar_rejected", rule="positive_prices", reason=err, open_time=open_time)
            return IngestResult(status=IngestStatus.REJECTED, reason=err, rule="positive_prices")

        if not is_aligned_open_time(open_time, normalized.timeframe):
            reason = f"open_time not aligned to {normalized.timeframe.value} UTC boundary"
            logger.warning("bar_rejected", rule="bar_alignment", reason=reason)
            return IngestResult(status=IngestStatus.REJECTED, reason=reason, rule="bar_alignment")

        async with self.session_factory() as session:
            repo = OHLCVBarRepository(session)

            if await repo.exists(normalized.instrument.id, normalized.timeframe, open_time):
                logger.info("bar_duplicate", open_time=open_time)
                return IngestResult(status=IngestStatus.DUPLICATE, reason="Duplicate bar")

            latest_row = await repo.get_latest(normalized.instrument.id, normalized.timeframe)
            if latest_row and open_time < latest_row.open_time:
                reason = "Out-of-order bar rejected"
                logger.warning("bar_rejected", rule="out_of_order", open_time=open_time)
                return IngestResult(
                    status=IngestStatus.REJECTED,
                    reason=reason,
                    rule="out_of_order",
                )

            lookback_rows = await repo.get_bars_before(
                normalized.instrument.id,
                normalized.timeframe,
                open_time,
                self.config.outlier_atr_lookback + 1,
            )
            prior_bars = [
                bar_to_domain(r, normalized.instrument) for r in lookback_rows
            ]
            atr = compute_atr(prior_bars, self.config.outlier_atr_lookback)
            outlier = is_outlier_bar(
                normalized, atr, self.config.outlier_atr_multiplier
            )
            flags = list(normalized.quality_flags)
            if outlier:
                flags.append("outlier_range")

            final_bar = OHLCVBar(
                instrument=normalized.instrument,
                timeframe=normalized.timeframe,
                open_time=open_time,
                open=normalized.open,
                high=normalized.high,
                low=normalized.low,
                close=normalized.close,
                volume=normalized.volume,
                is_outlier=outlier,
                quality_flags=flags,
            )

            inserted = await repo.insert(final_bar)
            if not inserted:
                return IngestResult(status=IngestStatus.DUPLICATE, reason="Duplicate bar")

            if latest_row:
                self._detect_gap(normalized, latest_row.open_time, open_time)

        await self.bar_cache.set_latest(final_bar)

        self.event_bus.publish(
            DomainEvent(
                event_type="market_data.bar.received",
                correlation_id=f"bar-{normalized.instrument.symbol}-{open_time.isoformat()}",
                payload={
                    "symbol": normalized.instrument.symbol,
                    "timeframe": normalized.timeframe.value,
                    "open_time": open_time.isoformat(),
                    "is_outlier": final_bar.is_outlier,
                },
            )
        )
        logger.info(
            "bar_accepted",
            symbol=normalized.instrument.symbol,
            timeframe=normalized.timeframe.value,
            open_time=open_time.isoformat(),
            is_outlier=final_bar.is_outlier,
        )
        return IngestResult(status=IngestStatus.ACCEPTED, bar=final_bar)

    def _detect_gap(
        self,
        bar: OHLCVBar,
        last_open: datetime,
        current_open: datetime,
    ) -> None:
        """Emit gap event if missing bars exceed tolerance."""
        expected = expected_next_open_time(last_open, bar.timeframe)
        if current_open <= expected:
            return

        minutes = TIMEFRAME_MINUTES[bar.timeframe]
        delta_minutes = int((current_open - expected).total_seconds() / 60)
        missing = delta_minutes // minutes

        if missing <= self.config.gap_tolerance_bars:
            return

        gap = GapRecord(
            instrument_symbol=bar.instrument.symbol,
            timeframe=bar.timeframe,
            expected_open_time=expected,
            actual_open_time=current_open,
            missing_bars=missing,
        )
        logger.warning("bar_gap_detected", missing_bars=missing, expected=expected.isoformat())
        self.event_bus.publish(
            DomainEvent(
                event_type="market_data.gap.detected",
                correlation_id=f"gap-{bar.instrument.symbol}-{current_open.isoformat()}",
                payload={
                    "symbol": gap.instrument_symbol,
                    "timeframe": gap.timeframe.value,
                    "expected_open_time": gap.expected_open_time.isoformat(),
                    "actual_open_time": gap.actual_open_time.isoformat(),
                    "missing_bars": gap.missing_bars,
                },
            )
        )

    async def get_latest(self, instrument: Instrument, timeframe: Timeframe) -> OHLCVBar | None:
        """Return latest bar from cache or database."""
        cached = await self.bar_cache.get_latest(instrument.symbol, timeframe)
        if cached:
            return OHLCVBar(
                instrument=instrument,
                timeframe=timeframe,
                open_time=datetime.fromisoformat(cached["open_time"]),
                open=Decimal(cached["open"]),
                high=Decimal(cached["high"]),
                low=Decimal(cached["low"]),
                close=Decimal(cached["close"]),
                volume=Decimal(cached["volume"]),
                is_outlier=cached.get("is_outlier", False),
                quality_flags=cached.get("quality_flags", []),
            )

        async with self.session_factory() as session:
            repo = OHLCVBarRepository(session)
            row = await repo.get_latest(instrument.id, timeframe)
            if not row:
                return None
            return bar_to_domain(row, instrument)

    async def get_history(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        limit: int = 500,
    ) -> list[OHLCVBar]:
        """Return historical bars in range."""
        async with self.session_factory() as session:
            repo = OHLCVBarRepository(session)
            rows = await repo.get_history(instrument.id, timeframe, start, end, limit)
            return [bar_to_domain(r, instrument) for r in rows]

    async def get_instrument(self, symbol: str) -> Instrument | None:
        """Resolve instrument by symbol."""
        async with self.session_factory() as session:
            return await InstrumentRepository(session).get_by_symbol(symbol)

    async def list_instruments(self) -> list[Instrument]:
        """List active instruments."""
        async with self.session_factory() as session:
            return await InstrumentRepository(session).list_active()

    async def get_recent_bars(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        limit: int,
        as_of: datetime | None = None,
    ) -> list[OHLCVBar]:
        """Return recent bars up to as_of (no look-ahead)."""
        from atlas.domain.services.bar_validation import to_utc

        as_of_dt = to_utc(as_of) if as_of else datetime.now(UTC)
        async with self.session_factory() as session:
            repo = OHLCVBarRepository(session)
            rows = await repo.get_bars_up_to(instrument.id, timeframe, as_of_dt, limit)
            return [bar_to_domain(r, instrument) for r in rows]
