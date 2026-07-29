"""Key level proximity scoring tests."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

from atlas.domain.models.enums import Bias, Timeframe, Trend
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.price_action import CandlePattern
from atlas.domain.models.price_level import PriceLevel
from atlas.domain.models.smc import SMCAnalysisResult
from atlas.domain.services.key_level_proximity import apply_proximity_scoring, proximity_multiplier


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def _empty_smc() -> SMCAnalysisResult:
    return SMCAnalysisResult(
        instrument=_instrument(),
        timeframe=Timeframe.M15,
        trend=Trend.RANGING,
        last_bos=None,
        last_choch=None,
        order_blocks=(),
        liquidity_pools=(),
        fair_value_gaps=(),
        directional_bias=Bias.NEUTRAL,
        computed_at=datetime.now(UTC),
    )


def test_support_level_uses_highest_multiplier() -> None:
    levels = [PriceLevel(price=Decimal("100"), strength=Decimal("0.8"), level_type="support")]
    multiplier = proximity_multiplier(
        Decimal("100.10"),
        levels,
        _empty_smc(),
        Decimal("0.0015"),
    )
    assert multiplier == Decimal("1.5")


def test_no_level_nearby_uses_default_multiplier() -> None:
    levels = [PriceLevel(price=Decimal("120"), strength=Decimal("0.8"), level_type="support")]
    multiplier = proximity_multiplier(
        Decimal("100"),
        levels,
        _empty_smc(),
        Decimal("0.0015"),
    )
    assert multiplier == Decimal("0.6")


def test_patterns_ranked_by_strength_after_proximity() -> None:
    bar = MagicMock()
    bar.close = Decimal("100")
    patterns = [
        CandlePattern("pin_bar", Bias.BULLISH, 0, Decimal("0.55"), False),
        CandlePattern("engulfing", Bias.BULLISH, 0, Decimal("0.65"), False),
    ]
    levels = [PriceLevel(price=Decimal("100"), strength=Decimal("0.8"), level_type="support")]
    scored = apply_proximity_scoring(
        patterns,
        [bar],
        levels,
        _empty_smc(),
        proximity_pct=Decimal("0.0015"),
        min_pattern_strength=Decimal("0.30"),
    )
    assert max(pattern.strength for pattern in scored) == Decimal("0.975")
    assert min(pattern.strength for pattern in scored) == Decimal("0.825")
    assert all(pattern.at_key_level for pattern in scored)
