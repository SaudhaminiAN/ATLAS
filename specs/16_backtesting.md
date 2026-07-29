# Spec 16 — Backtesting

## Objective

Replay historical data through the **same Analysis Pipeline** with zero look-ahead.

## Scope

### In Scope

- Chronological bar replay via `MarketDataReplayProtocol` (Spec 02)
- `AnalysisPipelineOrchestrator.run_replay` (Spec 20)
- Simulated execution (optional, Phase 2+)
- CLI report

### Out of Scope

- Grid search, tick-level, multi-instrument

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| `BacktestConfig` | CLI / API | Yes |
| `ohlcv_bars` or CSV | Spec 02 | Yes |
| Active `StrategyProfile` | Spec 18 | Yes |

## Outputs

| Output | Type | Consumers |
|--------|------|-----------|
| `BacktestResult` | Report | CLI, Analytics (14) |
| Decision log | `decisions` (optional persist) | Journal (13) |

## Interfaces

```python
class BacktestRunnerProtocol(Protocol):
    async def run(self, config: BacktestConfig) -> BacktestResult: ...
```

Uses `MarketDataReplayProtocol` + `AnalysisPipelineOrchestratorProtocol.run_replay`.

## Database

| Table / Cache | Operation | Owner |
|---------------|-----------|-------|
| `ohlcv_bars` | READ | Spec 02 |
| `decisions` | INSERT (optional flag) | Spec 17 |

## No Look-Ahead Rules

| Rule | Enforcement |
|------|-------------|
| Bar access at T | Only `open_time <= T` |
| Higher TF | Last closed bar as of T |
| Indicators | Rolling window only |
| Swings | 2-bar confirmation delay |
| Spy test | Assert no future bar accessed |

## Edge Cases

| Case | Behavior |
|------|----------|
| Gap in historical data | Log; continue (same as live) |
| No decisions in range | Empty result, not error |
| `risk_enabled` in backtest | Configurable; default match live phase |

## Acceptance Criteria

- [ ] Chronological order
- [ ] Same pipeline as live
- [ ] Look-ahead spy test passes
- [ ] WAIT logged with reasons
- [ ] Module accuracy in output
- [ ] CLI JSON report
- [ ] Golden test: 100-bar fixture

## Dependencies

- Spec 02 (replay), 20 (pipeline), 17, 14, 08–09, 18–19

## Notes

Implement in Phase 2 per `docs/mvp_roadmap.md`.
