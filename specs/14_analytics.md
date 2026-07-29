# Spec 14 — Analytics

## Objective

Compute trade performance and **module-level accuracy** metrics.

## Scope

### In Scope

- Trade metrics (win rate, profit factor, drawdown, equity curve)
- Decision metrics (WAIT rate, reason breakdown)
- Module accuracy per evidence source
- REST endpoints
- Event handlers

### Out of Scope

- Monte Carlo, benchmark comparison

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| `decisions` table | Spec 17 / 13 | Yes |
| `trades` table | Spec 11 | For trade metrics |
| `trade_events` | Spec 12 | For lifecycle |
| Date / profile filters | REST query params | Optional |

## Outputs

| Output | Type | Consumers |
|--------|------|-----------|
| `PerformanceSummary` | DTO | Frontend (21) |
| `DecisionStats` | DTO | Frontend (21) |
| `ModuleAccuracy` | DTO | Frontend (21) |

## Interfaces

```python
class AnalyticsServiceProtocol(Protocol):
    def get_performance_summary(self, filters: AnalyticsFilters) -> PerformanceSummary: ...
    def get_decision_stats(self, filters: AnalyticsFilters) -> DecisionStats: ...
    def get_module_accuracy(self, filters: AnalyticsFilters) -> list[ModuleAccuracy]: ...
    def get_equity_curve(self, filters: AnalyticsFilters) -> list[EquityPoint]: ...
```

## Database

| Table / Cache | Operation | Owner |
|---------------|-----------|-------|
| `decisions` | READ | Spec 17 |
| `trades` | READ | Spec 11 |
| None written | — | — |

## Module Accuracy Formulas

Evaluated over a date range with closed trades (or backtest outcomes).

### Per evidence source `S` (e.g. `smc_structure`, `mtf_alignment`):

```
appearances = decisions where evidence item source == S and score >= 0.30

true_positive = appearances on trades where realized_pnl > 0
false_signal  = appearances on trades where realized_pnl < 0
neutral_wait  = appearances on WAIT decisions (tracked separately)

true_positive_rate  = true_positive / max(appearances on closed trades, 1)
false_signal_rate   = false_signal / max(appearances on closed trades, 1)
```

### WAIT correctness (Phase 2 / backtest hook)

```
For each WAIT decision at time T:
  Simulate: would BUY and SELL have hit SL before TP using forward bars?
  If both would lose → WAIT was correct (+1 to wait_correct_count)

wait_correctness_rate = wait_correct / total_wait_decisions
```

### Decision stats

```
wait_rate = wait_count / total_decisions
actionable_rate = actionable_count / total_decisions
top_wait_reasons = group by decision.reason, order by count DESC, limit 10
```

## Edge Cases

| Case | Behavior |
|------|----------|
| Zero trades | Trade metrics zeroed; decision stats still computed |
| Zero decisions | All metrics zeroed (not error) |
| Module never appears | `total_appearances = 0`, rates = 0 |

## Acceptance Criteria

- [ ] Formulas match definitions above
- [ ] Decision stats without trades (Phase 1)
- [ ] Module accuracy after backtest/trades (Phase 2)
- [ ] Empty history → zeroed metrics
- [ ] Unit tests with fixtures

## Dependencies

- Spec 13, 17

## Downstream Consumers

- Frontend (21), AI (15)
