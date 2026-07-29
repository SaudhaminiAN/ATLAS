"""Support and resistance level detection (Spec 05)."""

from decimal import Decimal

from atlas.domain.models.price_level import PriceLevel
from atlas.domain.models.swing import SwingPoint

STRENGTH_BY_TOUCHES = {
    1: Decimal("0.3"),
    2: Decimal("0.5"),
    3: Decimal("0.75"),
}


def _strength_for_touches(touches: int) -> Decimal:
    if touches >= 4:
        return Decimal("1.0")
    return STRENGTH_BY_TOUCHES.get(touches, Decimal("0.3"))


def _merge_prices(
    points: list[SwingPoint],
    merge_tolerance_pct: Decimal,
) -> list[tuple[Decimal, int]]:
    """Cluster swing prices within tolerance; return (price, touches)."""
    if not points:
        return []

    clusters: list[dict] = []
    for point in sorted(points, key=lambda p: p.price):
        merged = False
        for cluster in clusters:
            center = cluster["price"]
            if center == 0:
                continue
            if abs(point.price - center) / center <= merge_tolerance_pct:
                touches = cluster["touches"] + 1
                new_price = (center * cluster["touches"] + point.price) / Decimal(touches)
                cluster["price"] = new_price
                cluster["touches"] = touches
                merged = True
                break
        if not merged:
            clusters.append({"price": point.price, "touches": 1})

    return [(cluster["price"], cluster["touches"]) for cluster in clusters]


def build_key_levels(
    swings: list[SwingPoint],
    merge_tolerance_pct: Decimal = Decimal("0.001"),
) -> list[PriceLevel]:
    """Build merged S/R levels with strength scores; top 5 (max 3 each side)."""
    highs = [s for s in swings if s.swing_type == "high"]
    lows = [s for s in swings if s.swing_type == "low"]

    resistance = [
        PriceLevel(price=price, strength=_strength_for_touches(touches), level_type="resistance")
        for price, touches in _merge_prices(highs, merge_tolerance_pct)
    ]
    support = [
        PriceLevel(price=price, strength=_strength_for_touches(touches), level_type="support")
        for price, touches in _merge_prices(lows, merge_tolerance_pct)
    ]

    resistance.sort(key=lambda level: level.strength, reverse=True)
    support.sort(key=lambda level: level.strength, reverse=True)

    selected = support[:3] + resistance[:3]
    selected.sort(key=lambda level: level.strength, reverse=True)
    return selected[:5]


def nearest_levels(
    close: Decimal,
    key_levels: list[PriceLevel],
) -> tuple[Decimal | None, Decimal | None]:
    """Return nearest support below and resistance above close."""
    supports = [
        level.price
        for level in key_levels
        if level.level_type == "support" and level.price < close
    ]
    resistances = [
        level.price
        for level in key_levels
        if level.level_type == "resistance" and level.price > close
    ]

    nearest_support = max(supports) if supports else None
    nearest_resistance = min(resistances) if resistances else None
    return nearest_support, nearest_resistance
