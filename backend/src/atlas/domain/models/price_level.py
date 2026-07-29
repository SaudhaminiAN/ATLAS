"""Shared price level model."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PriceLevel:
    """Support or resistance level with strength score."""

    price: Decimal
    strength: Decimal
    level_type: str
