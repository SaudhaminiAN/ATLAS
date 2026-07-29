"""Analytics metric unit tests (Spec 14)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from atlas.domain.models.confluence import ConfluenceResult, EvidenceItem
from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.enums import Direction
from atlas.domain.models.instrument import Instrument
from atlas.domain.services.analytics_metrics import (
    compute_decision_stats,
    compute_module_accuracy,
    empty_decision_stats,
    empty_performance_summary,
)


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def _decision(
    direction: Direction,
    *,
    reason: str = "test",
    evidence: tuple[EvidenceItem, ...] = (),
    is_actionable: bool | None = None,
) -> TradingDecision:
    instrument = _instrument()
    confluence = ConfluenceResult(
        instrument=instrument,
        suggested_direction=direction,
        total_score=Decimal("0.5"),
        raw_score=Decimal("0.5"),
        bullish_raw=Decimal("0.5"),
        bearish_raw=Decimal("0"),
        news_penalty=Decimal("0"),
        module_scores=(),
        evidence=evidence,
        evidence_count=len(evidence),
        has_conflict=False,
        strategy_profile_id="xauusd_conservative",
        computed_at=datetime.now(UTC),
    )
    return TradingDecision(
        id=uuid4(),
        instrument=instrument,
        direction=direction,
        is_actionable=is_actionable if is_actionable is not None else direction != Direction.WAIT,
        confluence_score=Decimal("0.5"),
        strategy_id="xauusd_conservative",
        reason=reason,
        correlation_id="cid",
        decided_at=datetime.now(UTC),
        confluence_snapshot=confluence,
    )


def test_empty_decision_stats() -> None:
    stats = compute_decision_stats([])
    assert stats == empty_decision_stats()


def test_decision_stats_formulas() -> None:
    decisions = [
        _decision(Direction.WAIT, reason="low confluence"),
        _decision(Direction.WAIT, reason="low confluence"),
        _decision(Direction.BUY, is_actionable=True),
        _decision(Direction.SELL, is_actionable=True),
        _decision(Direction.WAIT, reason="news blocked"),
    ]
    stats = compute_decision_stats(decisions)

    assert stats.total_decisions == 5
    assert stats.wait_count == 3
    assert stats.buy_count == 1
    assert stats.sell_count == 1
    assert stats.actionable_count == 2
    assert stats.wait_rate == Decimal("0.6")
    assert stats.actionable_rate == Decimal("0.4")
    assert stats.top_wait_reasons[0].reason == "low confluence"
    assert stats.top_wait_reasons[0].count == 2


def test_module_accuracy_counts_evidence() -> None:
    evidence = (
        EvidenceItem(
            source="mtf_alignment",
            direction=Direction.WAIT,
            weight=Decimal("0.25"),
            score=Decimal("0.35"),
            weighted_contribution=Decimal("0.09"),
            description="neutral",
        ),
        EvidenceItem(
            source="smc_structure",
            direction=Direction.BUY,
            weight=Decimal("0.25"),
            score=Decimal("0.10"),
            weighted_contribution=Decimal("0.025"),
            description="weak",
        ),
    )
    decisions = [
        _decision(Direction.WAIT, evidence=evidence),
        _decision(Direction.BUY, evidence=evidence[:1]),
    ]
    modules = compute_module_accuracy(decisions)

    mtf = next(m for m in modules if m.source == "mtf_alignment")
    assert mtf.appearances == 2
    assert mtf.neutral_wait == 1
    assert mtf.true_positive_rate == Decimal("0")
    assert all(m.source != "smc_structure" for m in modules)


def test_empty_performance_summary_zeros() -> None:
    summary = empty_performance_summary()
    assert summary.total_trades == 0
    assert summary.win_rate == Decimal("0")
