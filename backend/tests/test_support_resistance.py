"""Support and resistance level tests."""

from decimal import Decimal

from atlas.domain.models.price_level import PriceLevel
from atlas.domain.models.swing import SwingPoint
from atlas.domain.services.support_resistance import (
    build_key_levels,
    nearest_levels,
)


def test_strength_by_touch_count() -> None:
    swings = [
        SwingPoint(1, Decimal("100.0"), "low"),
        SwingPoint(2, Decimal("100.05"), "low"),
        SwingPoint(3, Decimal("100.08"), "low"),
        SwingPoint(4, Decimal("120.0"), "high"),
    ]
    levels = build_key_levels(swings, merge_tolerance_pct=Decimal("0.001"))
    support = next(level for level in levels if level.level_type == "support")
    assert support.strength == Decimal("0.75")


def test_max_three_per_side() -> None:
    swings = [
        SwingPoint(i, Decimal(100 + i), "low")
        for i in range(5)
    ] + [
        SwingPoint(i + 10, Decimal(200 + i), "high")
        for i in range(5)
    ]
    levels = build_key_levels(swings, merge_tolerance_pct=Decimal("0.0001"))
    supports = [level for level in levels if level.level_type == "support"]
    resistances = [level for level in levels if level.level_type == "resistance"]
    assert len(supports) <= 3
    assert len(resistances) <= 3
    assert len(levels) <= 5


def test_nearest_levels_null_when_missing() -> None:
    close = Decimal("150")
    levels = [
        PriceLevel(Decimal("160"), Decimal("0.5"), "resistance"),
        PriceLevel(Decimal("140"), Decimal("0.5"), "support"),
    ]
    support, resistance = nearest_levels(close, levels)
    assert support == Decimal("140")
    assert resistance == Decimal("160")


def test_nearest_levels_none_when_no_match() -> None:
    close = Decimal("150")
    levels = [
        PriceLevel(Decimal("160"), Decimal("0.5"), "resistance"),
    ]
    support, resistance = nearest_levels(close, levels)
    assert support is None
    assert resistance == Decimal("160")
