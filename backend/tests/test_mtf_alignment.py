"""MTF alignment and conflict tests."""

from decimal import Decimal

from atlas.domain.models.enums import Bias, Timeframe
from atlas.domain.models.mtf import TimeframeBias
from atlas.domain.services.mtf_alignment import compute_alignment, detect_conflicts


def _bias(tf: Timeframe, bias: Bias) -> TimeframeBias:
    return TimeframeBias(
        timeframe=tf,
        bias=bias,
        confidence=Decimal("0.6"),
        trend_source="test",
        key_levels=(),
    )


def test_aligned_bullish_majority() -> None:
    biases = [
        _bias(Timeframe.D1, Bias.BULLISH),
        _bias(Timeframe.H4, Bias.BULLISH),
        _bias(Timeframe.H1, Bias.BULLISH),
        _bias(Timeframe.M15, Bias.NEUTRAL),
    ]
    score, dominant, aligned = compute_alignment(biases)
    assert dominant == Bias.BULLISH
    assert score == Decimal("0.75")
    assert aligned is True


def test_all_neutral_not_aligned() -> None:
    biases = [
        _bias(Timeframe.D1, Bias.NEUTRAL),
        _bias(Timeframe.H4, Bias.NEUTRAL),
    ]
    score, dominant, aligned = compute_alignment(biases)
    assert dominant == Bias.NEUTRAL
    assert score == Decimal("0.0")
    assert aligned is False


def test_single_timeframe_non_neutral() -> None:
    biases = [_bias(Timeframe.M15, Bias.BEARISH)]
    score, dominant, aligned = compute_alignment(biases)
    assert score == Decimal("1.0")
    assert dominant == Bias.BEARISH
    assert aligned is True


def test_adjacent_conflict_detected() -> None:
    biases = [
        _bias(Timeframe.D1, Bias.BULLISH),
        _bias(Timeframe.H4, Bias.BEARISH),
        _bias(Timeframe.H1, Bias.BEARISH),
        _bias(Timeframe.M15, Bias.BEARISH),
    ]
    has_conflict, distant = detect_conflicts(
        biases,
        [Timeframe.D1, Timeframe.H4, Timeframe.H1, Timeframe.M15],
    )
    assert has_conflict is True
    assert distant is False


def test_distant_conflict_without_adjacent() -> None:
    biases = [
        _bias(Timeframe.D1, Bias.BULLISH),
        _bias(Timeframe.H4, Bias.NEUTRAL),
        _bias(Timeframe.H1, Bias.NEUTRAL),
        _bias(Timeframe.M15, Bias.BEARISH),
    ]
    has_conflict, distant = detect_conflicts(
        biases,
        [Timeframe.D1, Timeframe.H4, Timeframe.H1, Timeframe.M15],
    )
    assert has_conflict is False
    assert distant is True


def test_tie_returns_zero_alignment() -> None:
    biases = [
        _bias(Timeframe.D1, Bias.BULLISH),
        _bias(Timeframe.H4, Bias.BEARISH),
    ]
    score, dominant, aligned = compute_alignment(biases)
    assert score == Decimal("0.0")
    assert dominant == Bias.NEUTRAL
    assert aligned is False
