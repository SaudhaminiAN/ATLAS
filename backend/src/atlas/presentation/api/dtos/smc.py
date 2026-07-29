"""SMC API DTOs."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class StructureBreakDTO(BaseModel):
    """BOS or CHoCH break."""

    break_type: str
    direction: str
    bar_index: int
    price: Decimal


class OrderBlockDTO(BaseModel):
    """Order block zone."""

    direction: str
    bar_index: int
    zone_low: Decimal
    zone_high: Decimal


class LiquidityPoolDTO(BaseModel):
    """Liquidity pool."""

    pool_type: str
    price: Decimal
    touch_count: int
    strength: Decimal


class FairValueGapDTO(BaseModel):
    """Fair value gap."""

    direction: str
    bar_index: int
    gap_low: Decimal
    gap_high: Decimal


class SMCAnalysisDTO(BaseModel):
    """SMC analysis snapshot."""

    symbol: str
    timeframe: str
    trend: str
    directional_bias: str
    last_bos: StructureBreakDTO | None
    last_choch: StructureBreakDTO | None
    order_blocks: list[OrderBlockDTO]
    liquidity_pools: list[LiquidityPoolDTO]
    fair_value_gaps: list[FairValueGapDTO]
    computed_at: datetime
