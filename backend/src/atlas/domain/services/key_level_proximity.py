"""Key level proximity scoring for price action (Spec 07)."""

from decimal import Decimal

from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.price_action import CandlePattern
from atlas.domain.models.price_level import PriceLevel
from atlas.domain.models.smc import SMCAnalysisResult


def _near_price(price: Decimal, level: Decimal, proximity_pct: Decimal) -> bool:
    if level <= 0:
        return False
    return abs(price - level) / level <= proximity_pct


def _near_zone(
    price: Decimal,
    zone_low: Decimal,
    zone_high: Decimal,
    proximity_pct: Decimal,
) -> bool:
    if zone_low <= price <= zone_high:
        return True
    midpoint = zone_low + (zone_high - zone_low) / 2
    return _near_price(price, midpoint, proximity_pct)


def proximity_multiplier(
    price: Decimal,
    key_levels: list[PriceLevel],
    smc: SMCAnalysisResult,
    proximity_pct: Decimal,
) -> Decimal:
    """Return the best proximity multiplier for a price."""
    multipliers = [Decimal("0.6")]

    for level in key_levels:
        if _near_price(price, level.price, proximity_pct):
            multipliers.append(Decimal("1.5"))

    for block in smc.order_blocks:
        if _near_zone(price, block.zone_low, block.zone_high, proximity_pct):
            multipliers.append(Decimal("1.5"))

    for pool in smc.liquidity_pools:
        if _near_price(price, pool.price, proximity_pct):
            multipliers.append(Decimal("1.3"))

    for gap in smc.fair_value_gaps:
        if _near_zone(price, gap.gap_low, gap.gap_high, proximity_pct):
            multipliers.append(Decimal("1.2"))

    return max(multipliers)


def apply_proximity_scoring(
    patterns: list[CandlePattern],
    bars: list[OHLCVBar],
    key_levels: list[PriceLevel],
    smc: SMCAnalysisResult,
    *,
    proximity_pct: Decimal,
    min_pattern_strength: Decimal,
) -> list[CandlePattern]:
    """Apply key-level proximity multipliers and filter weak patterns."""
    if not patterns:
        return []

    close = bars[patterns[0].bar_index].close
    multiplier = proximity_multiplier(close, key_levels, smc, proximity_pct)
    at_key_level = multiplier > Decimal("0.6")

    scored: list[CandlePattern] = []
    for pattern in patterns:
        strength = min(pattern.strength * multiplier, Decimal("1.0"))
        if strength < min_pattern_strength:
            continue
        scored.append(
            CandlePattern(
                pattern_type=pattern.pattern_type,
                direction=pattern.direction,
                bar_index=pattern.bar_index,
                strength=strength,
                at_key_level=at_key_level,
            )
        )

    return scored
