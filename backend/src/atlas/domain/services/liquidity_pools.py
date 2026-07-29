"""Liquidity pool detection (Spec 06)."""

from decimal import Decimal

from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.smc import LiquidityPool
from atlas.domain.services.swing_detection import find_swing_highs, find_swing_lows


def _strength(touches: int) -> Decimal:
    if touches >= 4:
        return Decimal("1.0")
    if touches == 3:
        return Decimal("0.75")
    if touches == 2:
        return Decimal("0.5")
    return Decimal("0.3")


def _cluster_levels(
    prices: list[Decimal],
    tolerance_pct: Decimal,
) -> list[tuple[Decimal, int]]:
    if not prices:
        return []

    clusters: list[dict] = []
    for price in sorted(prices):
        merged = False
        for cluster in clusters:
            center = cluster["price"]
            if center == 0:
                continue
            if abs(price - center) / center <= tolerance_pct:
                touches = cluster["touches"] + 1
                cluster["price"] = (center * cluster["touches"] + price) / Decimal(touches)
                cluster["touches"] = touches
                merged = True
                break
        if not merged:
            clusters.append({"price": price, "touches": 1})

    return [
        (cluster["price"], cluster["touches"])
        for cluster in clusters
        if cluster["touches"] >= 2
    ]


def detect_liquidity_pools(
    bars: list[OHLCVBar],
    *,
    swing_lookback: int = 2,
    equal_level_tolerance_pct: Decimal = Decimal("0.001"),
) -> list[LiquidityPool]:
    """Detect equal-high and equal-low liquidity pools."""
    highs = [price for _, price in find_swing_highs(bars, swing_lookback)]
    lows = [price for _, price in find_swing_lows(bars, swing_lookback)]

    pools: list[LiquidityPool] = []
    for price, touches in _cluster_levels(highs, equal_level_tolerance_pct):
        pools.append(
            LiquidityPool(
                pool_type="equal_highs",
                price=price,
                touch_count=touches,
                strength=_strength(touches),
            )
        )
    for price, touches in _cluster_levels(lows, equal_level_tolerance_pct):
        pools.append(
            LiquidityPool(
                pool_type="equal_lows",
                price=price,
                touch_count=touches,
                strength=_strength(touches),
            )
        )
    return pools
