"""Spread assessment (v1 stub, Spec 03)."""

from decimal import Decimal

from atlas.domain.models.enums import SpreadStatus


def assess_spread(
    spread: Decimal | None,
    spread_history: list[Decimal] | None = None,
    *,
    elevated_multiplier: Decimal = Decimal("1.5"),
    average_lookback: int = 20,
) -> SpreadStatus:
    """Return spread status; defaults to normal when data unavailable."""
    if spread is None:
        return SpreadStatus.NORMAL

    if not spread_history or len(spread_history) < average_lookback:
        return SpreadStatus.NORMAL

    window = spread_history[-average_lookback:]
    average = sum(window) / Decimal(len(window))
    if average <= 0:
        return SpreadStatus.NORMAL

    if spread > elevated_multiplier * average:
        return SpreadStatus.ELEVATED
    return SpreadStatus.NORMAL
