"""Pure analytics metric calculations (Spec 14)."""

from collections import Counter
from decimal import Decimal

from atlas.domain.models.analytics import (
    DecisionStats,
    ModuleAccuracy,
    PerformanceSummary,
    WaitReasonCount,
)
from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.enums import Direction

MIN_EVIDENCE_SCORE = Decimal("0.30")
ZERO = Decimal("0")


def empty_decision_stats() -> DecisionStats:
    return DecisionStats(
        total_decisions=0,
        wait_count=0,
        buy_count=0,
        sell_count=0,
        actionable_count=0,
        wait_rate=ZERO,
        actionable_rate=ZERO,
        top_wait_reasons=(),
    )


def empty_performance_summary() -> PerformanceSummary:
    return PerformanceSummary(
        total_trades=0,
        winning_trades=0,
        losing_trades=0,
        win_rate=ZERO,
        profit_factor=ZERO,
        total_pnl=ZERO,
        max_drawdown=ZERO,
    )


def compute_decision_stats(decisions: list[TradingDecision]) -> DecisionStats:
    """Compute decision metrics per Spec 14."""
    total = len(decisions)
    if total == 0:
        return empty_decision_stats()

    wait_count = sum(1 for d in decisions if d.direction == Direction.WAIT)
    buy_count = sum(1 for d in decisions if d.direction == Direction.BUY)
    sell_count = sum(1 for d in decisions if d.direction == Direction.SELL)
    actionable_count = sum(1 for d in decisions if d.is_actionable)

    wait_rate = Decimal(wait_count) / Decimal(total)
    actionable_rate = Decimal(actionable_count) / Decimal(total)

    reason_counter: Counter[str] = Counter()
    for decision in decisions:
        if decision.direction == Direction.WAIT:
            reason_counter[decision.reason] += 1

    top_wait_reasons = tuple(
        WaitReasonCount(reason=reason, count=count)
        for reason, count in reason_counter.most_common(10)
    )

    return DecisionStats(
        total_decisions=total,
        wait_count=wait_count,
        buy_count=buy_count,
        sell_count=sell_count,
        actionable_count=actionable_count,
        wait_rate=wait_rate,
        actionable_rate=actionable_rate,
        top_wait_reasons=top_wait_reasons,
    )


def compute_module_accuracy(decisions: list[TradingDecision]) -> list[ModuleAccuracy]:
    """Compute per-source module accuracy (trade outcomes deferred until Spec 11)."""
    appearances: Counter[str] = Counter()
    neutral_wait: Counter[str] = Counter()
    true_positive: Counter[str] = Counter()
    false_signal: Counter[str] = Counter()
    closed_trade_appearances: Counter[str] = Counter()

    for decision in decisions:
        snapshot = decision.confluence_snapshot
        if snapshot is None:
            continue

        sources_in_decision: set[str] = set()
        for item in snapshot.evidence:
            if item.score < MIN_EVIDENCE_SCORE or item.source in sources_in_decision:
                continue
            sources_in_decision.add(item.source)
            appearances[item.source] += 1
            if decision.direction == Direction.WAIT:
                neutral_wait[item.source] += 1
            # Trade-linked TP/FP requires trades table (Spec 11) — counts stay zero.

    results: list[ModuleAccuracy] = []
    for source in sorted(appearances):
        tp = true_positive[source]
        fs = false_signal[source]
        trade_apps = closed_trade_appearances[source]
        denom = max(trade_apps, 1)
        results.append(
            ModuleAccuracy(
                source=source,
                appearances=appearances[source],
                true_positive=tp,
                false_signal=fs,
                neutral_wait=neutral_wait[source],
                true_positive_rate=Decimal(tp) / Decimal(denom),
                false_signal_rate=Decimal(fs) / Decimal(denom),
            )
        )
    return results
