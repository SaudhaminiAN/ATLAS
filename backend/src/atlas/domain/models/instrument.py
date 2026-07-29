"""Instrument entity."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Instrument:
    """Tradable instrument definition."""

    id: UUID
    symbol: str
    display_name: str
    pip_size: Decimal
    lot_size: Decimal
    is_active: bool = True

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("symbol is required")
