"""SMC analysis domain models."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from atlas.domain.models.enums import Bias, Timeframe, Trend
from atlas.domain.models.instrument import Instrument


@dataclass(frozen=True, slots=True)
class StructureBreak:
    """BOS or CHoCH structure break."""

    break_type: str
    direction: Bias
    bar_index: int
    price: Decimal


@dataclass(frozen=True, slots=True)
class OrderBlock:
    """Unmitigated order block zone."""

    direction: Bias
    bar_index: int
    zone_low: Decimal
    zone_high: Decimal
    is_mitigated: bool


@dataclass(frozen=True, slots=True)
class LiquidityPool:
    """Clustered equal highs or lows."""

    pool_type: str
    price: Decimal
    touch_count: int
    strength: Decimal


@dataclass(frozen=True, slots=True)
class FairValueGap:
    """Fair value gap zone."""

    direction: Bias
    bar_index: int
    gap_low: Decimal
    gap_high: Decimal
    is_filled: bool


@dataclass(frozen=True, slots=True)
class SMCAnalysisResult:
    """SMC analysis output per timeframe."""

    instrument: Instrument
    timeframe: Timeframe
    trend: Trend
    last_bos: StructureBreak | None
    last_choch: StructureBreak | None
    order_blocks: tuple[OrderBlock, ...]
    liquidity_pools: tuple[LiquidityPool, ...]
    fair_value_gaps: tuple[FairValueGap, ...]
    directional_bias: Bias
    computed_at: datetime
