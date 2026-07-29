# Spec 20 — Analysis Pipeline

## Objective

Orchestrate end-to-end analysis on each bar close — correct order, no look-ahead, single correlation ID.

## Scope

### In Scope

- `AnalysisPipelineOrchestrator`
- Trigger: `market_data.bar.received` on primary TF (M15)
- Sequential stages with parallel sub-tasks where noted
- Correlation ID propagation
- Pipeline state machine and deduplication
- Domain events: `pipeline.completed`, `pipeline.failed`
- Persist `pipeline_runs` for debugging

### Out of Scope

- Execution (separate, post-decision)
- Backtest iterator logic (Spec 16 provides bars; same orchestrator)

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| `market_data.bar.received` | Spec 02 | Yes |
| Active `StrategyProfile` | Spec 18 | Yes |
| All stage services | Specs 03–10, 17, 19 | Per stage |

## Outputs

| Output | Type | Consumers |
|--------|------|-----------|
| `PipelineRun` | Domain model | Frontend (21), logging |
| `TradingDecision` | Via Spec 17 | Journal, Frontend |
| `pipeline.completed` / `pipeline.failed` | Events | Analytics, alerts |

## Interfaces

```python
class AnalysisPipelineOrchestratorProtocol(Protocol):
    async def run(
        self,
        instrument: Instrument,
        trigger_bar: OHLCVBar,
        correlation_id: str | None = None,
    ) -> PipelineRun: ...

    async def run_replay(
        self,
        instrument: Instrument,
        bar_iterator: AsyncIterator[OHLCVBar],
        config: BacktestConfig,
    ) -> list[PipelineRun]: ...
```

## Database

| Table / Cache | Operation | Owner |
|---------------|-----------|-------|
| `pipeline_runs` | INSERT | This spec |
| `pipeline:dedupe:{symbol}:{tf}:{time}` | Redis SET NX (TTL 60s) | This spec |

## Pipeline Stages

```
1. Market Context      (03)
2. Multi-TF Analysis   (04)  — parallel per TF
3. Technical Analysis  (05)  — parallel with 4, 6
4. SMC Analysis        (06)  — parallel with 3, 6
5. Price Action        (07)  — after 3, 4
6. News Filter         (19)
7. Confluence          (08)
8. Validation          (09)
9. Risk                (10)  — skipped if risk_enabled: false
10. Decision Engine    (17)
```

## Pipeline Rules

- **No look-ahead:** `open_time <= trigger_bar.open_time`
- **Fail gracefully:** non-critical stages (03–07 partial) continue with warning
- **Idempotent:** dedupe by `instrument + timeframe + open_time`

## Stage Classification

| Stage | Critical? | On Failure |
|-------|-----------|------------|
| Market Context | Yes | Abort → WAIT decision |
| MTF Analysis | Yes | Abort → WAIT |
| Technical / SMC / PA | No | Continue, log warning |
| News Filter | Yes | Abort → WAIT |
| Confluence | Yes | Abort → WAIT |
| Validation | Yes | Abort → WAIT |
| Risk | No | Skip if disabled; else WAIT if fails |
| Decision Engine | Yes | Abort → WAIT |

## Configuration

```yaml
pipeline:
  primary_timeframe: M15
  risk_enabled: false
  stage_timeout_seconds: 5
  dedupe_window_seconds: 60
```

## Domain Models

```python
@dataclass(frozen=True)
class PipelineRun:
    id: UUID
    correlation_id: str
    instrument: Instrument
    trigger_timeframe: Timeframe
    trigger_bar_time: datetime
    status: PipelineStatus
    stage_results: dict[str, StageResult]
    decision_id: UUID | None
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int | None
```

## Edge Cases

| Case | Behavior |
|------|----------|
| Duplicate bar trigger | Skip run; log info |
| Stage timeout | Critical → abort; non-critical → skip stage |
| Partial module failure | Continue with reduced evidence |
| Critical failure | Emit WAIT decision with `reason = stage error` |
| Concurrent runs same symbol | Queue or reject second (configurable) |

## Acceptance Criteria

- [ ] Triggered only on primary TF bar close
- [ ] Stages in order; correlation ID in all logs/events
- [ ] Dedup works
- [ ] No look-ahead unit test
- [ ] Non-critical failure doesn't abort
- [ ] Critical failure → WAIT with reason
- [ ] Full integration test
- [ ] `run_replay` used by Spec 16

## Dependencies

- Spec 02 (trigger), Specs 03–10, 17–19

## Downstream Consumers

- Backtesting (16), Frontend (21), Analytics (14)
