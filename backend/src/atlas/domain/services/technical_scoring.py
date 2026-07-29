"""Directional context scores for confluence (Spec 05)."""

from decimal import Decimal

from atlas.domain.models.enums import Trend

MAX_CONTEXT_SCORE = Decimal("0.5")


def compute_context_scores(
    trend: Trend,
    close: Decimal,
    ema20: Decimal | None,
    ema50: Decimal | None,
    rsi: Decimal | None,
) -> tuple[Decimal, Decimal]:
    """Return bullish and bearish context scores, each capped at 0.5."""
    bullish = Decimal(0)
    bearish = Decimal(0)

    if trend == Trend.UPTREND:
        bullish += Decimal("0.3")
    elif trend == Trend.DOWNTREND:
        bearish += Decimal("0.3")

    if ema20 is not None and ema50 is not None:
        if close > ema20 > ema50:
            bullish += Decimal("0.2")
        elif close < ema20 < ema50:
            bearish += Decimal("0.2")

    if rsi is not None and Decimal(40) <= rsi <= Decimal(60):
        bullish += Decimal("0.1")
        bearish += Decimal("0.1")

    return (
        min(bullish, MAX_CONTEXT_SCORE),
        min(bearish, MAX_CONTEXT_SCORE),
    )
