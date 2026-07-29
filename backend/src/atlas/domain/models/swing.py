"""Swing point model (shared Spec 03/05/06)."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class SwingPoint:
    """Confirmed swing high or low."""

    bar_index: int
    price: Decimal
    swing_type: str
