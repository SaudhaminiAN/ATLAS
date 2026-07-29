"""Monetary value objects."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Money:
    """Amount in account currency."""

    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        if self.currency != self.currency.upper():
            object.__setattr__(self, "currency", self.currency.upper())


@dataclass(frozen=True, slots=True)
class Price:
    """Instrument price with pip context."""

    value: Decimal
    instrument_symbol: str

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError("price must be positive")
