"""Domain model unit tests."""

from decimal import Decimal
from uuid import uuid4

import pytest

from atlas.domain.models.enums import Direction, Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.money import Money, Price


def test_instrument_creation() -> None:
    """Instrument stores symbol and pip metadata."""
    inst = Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )
    assert inst.symbol == "XAUUSD"
    assert inst.is_active is True


def test_instrument_requires_symbol() -> None:
    """Empty symbol raises ValueError."""
    with pytest.raises(ValueError, match="symbol"):
        Instrument(
            id=uuid4(),
            symbol="",
            display_name="Gold",
            pip_size=Decimal("0.01"),
            lot_size=Decimal("100"),
        )


def test_price_must_be_positive() -> None:
    """Non-positive price is rejected."""
    with pytest.raises(ValueError, match="positive"):
        Price(value=Decimal("0"), instrument_symbol="XAUUSD")


def test_money_normalizes_currency() -> None:
    """Currency code is uppercased."""
    money = Money(amount=Decimal("100"), currency="usd")
    assert money.currency == "USD"


def test_direction_enum_values() -> None:
    """Direction enum includes WAIT default state."""
    assert Direction.WAIT.value == "WAIT"
    assert Timeframe.M15.value == "M15"
