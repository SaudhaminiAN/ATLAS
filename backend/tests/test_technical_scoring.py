"""Technical scoring tests."""

from decimal import Decimal

from atlas.domain.models.enums import Trend
from atlas.domain.services.technical_scoring import compute_context_scores


def test_bullish_score_capped_at_half() -> None:
    bullish, bearish = compute_context_scores(
        Trend.UPTREND,
        Decimal("2360"),
        Decimal("2355"),
        Decimal("2350"),
        Decimal("50"),
    )
    assert bullish == Decimal("0.5")
    assert bearish == Decimal("0.1")


def test_bearish_score_capped_at_half() -> None:
    bullish, bearish = compute_context_scores(
        Trend.DOWNTREND,
        Decimal("2340"),
        Decimal("2350"),
        Decimal("2360"),
        Decimal("50"),
    )
    assert bearish == Decimal("0.5")
    assert bullish == Decimal("0.1")
