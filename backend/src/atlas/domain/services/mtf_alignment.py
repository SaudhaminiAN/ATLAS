"""MTF alignment score and conflict detection (Spec 04)."""

from decimal import Decimal

from atlas.domain.models.enums import Bias, Timeframe
from atlas.domain.models.mtf import TimeframeBias

DEFAULT_ALIGNMENT_THRESHOLD = Decimal("0.75")

ADJACENT_PAIRS: tuple[tuple[Timeframe, Timeframe], ...] = (
    (Timeframe.D1, Timeframe.H4),
    (Timeframe.H4, Timeframe.H1),
    (Timeframe.H1, Timeframe.M15),
)


def _disagree(a: Bias, b: Bias) -> bool:
    return (
        a != Bias.NEUTRAL
        and b != Bias.NEUTRAL
        and a != b
    )


def compute_alignment(
    biases: list[TimeframeBias],
    threshold: Decimal = DEFAULT_ALIGNMENT_THRESHOLD,
) -> tuple[Decimal, Bias, bool]:
    """Return alignment score, dominant bias, and aligned flag."""
    if len(biases) == 1:
        bias = biases[0].bias
        score = Decimal("1.0") if bias != Bias.NEUTRAL else Decimal("0.0")
        return score, bias, score >= threshold

    bullish = sum(1 for item in biases if item.bias == Bias.BULLISH)
    bearish = sum(1 for item in biases if item.bias == Bias.BEARISH)
    total = len(biases)

    if bullish == bearish:
        return Decimal("0.0"), Bias.NEUTRAL, False

    if bullish > bearish:
        score = Decimal(bullish) / Decimal(total)
        return score.quantize(Decimal("0.01")), Bias.BULLISH, score >= threshold

    score = Decimal(bearish) / Decimal(total)
    return score.quantize(Decimal("0.01")), Bias.BEARISH, score >= threshold


def detect_conflicts(
    biases: list[TimeframeBias],
    active_timeframes: list[Timeframe],
) -> tuple[bool, bool]:
    """Return has_conflict (adjacent) and distant_conflict (D1 vs M15)."""
    bias_map = {item.timeframe: item.bias for item in biases}
    active_set = set(active_timeframes)

    has_conflict = False
    for tf1, tf2 in ADJACENT_PAIRS:
        if tf1 not in active_set or tf2 not in active_set:
            continue
        b1 = bias_map.get(tf1, Bias.NEUTRAL)
        b2 = bias_map.get(tf2, Bias.NEUTRAL)
        if _disagree(b1, b2):
            has_conflict = True
            break

    distant_conflict = False
    if Timeframe.D1 in active_set and Timeframe.M15 in active_set:
        d1 = bias_map.get(Timeframe.D1, Bias.NEUTRAL)
        m15 = bias_map.get(Timeframe.M15, Bias.NEUTRAL)
        if _disagree(d1, m15) and not has_conflict:
            distant_conflict = True

    return has_conflict, distant_conflict
