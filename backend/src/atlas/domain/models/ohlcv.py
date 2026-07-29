"""OHLCV bar domain models."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from atlas.domain.models.enums import Timeframe
from atlas.domain.models.instrument import Instrument


class IngestStatus(StrEnum):
    """Result of bar ingestion."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"


@dataclass(frozen=True, slots=True)
class OHLCVBar:
    """Normalized OHLCV candle."""

    instrument: Instrument
    timeframe: Timeframe
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    is_outlier: bool = False
    quality_flags: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class GapRecord:
    """Detected gap in bar sequence."""

    instrument_symbol: str
    timeframe: Timeframe
    expected_open_time: datetime
    actual_open_time: datetime
    missing_bars: int


@dataclass(frozen=True, slots=True)
class IngestResult:
    """Outcome of ingesting a single bar."""

    status: IngestStatus
    bar: OHLCVBar | None = None
    reason: str | None = None
    rule: str | None = None


@dataclass(frozen=True, slots=True)
class BarQualityReport:
    """Aggregated ingestion quality metrics."""

    total_received: int
    accepted: int
    rejected: int
    duplicates: int
    outliers: int
    gaps: list[GapRecord] = field(default_factory=list)
