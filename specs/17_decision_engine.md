# Spec 17 — Decision Engine

## Objective

Emit the final **BUY / SELL / WAIT** decision. Single authority for trade direction — no other module may emit a final signal.

## Scope

### In Scope

- `DecisionEngineService` — final decision logic
- Input aggregation from Confluence, Validation, Risk, Strategy, News
- Persist every decision to `decisions` table (including WAIT)
- Domain event: `decision.emitted`
- REST: `GET /decisions/{symbol}/latest`, `GET /decisions/{symbol}/history`
- WebSocket channel: `decisions.{symbol}`

### Out of Scope

- AI override of any rule
- Execution (Spec 11 subscribes to actionable only)
- Confluence or validation computation

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| `ConfluenceResult` | Spec 08 | Yes |
| `ValidationResult` | Spec 09 | Yes |
| `NewsFilterStatus` | Spec 19 | Yes |
| `StrategyProfile` | Spec 18 | Yes |
| `RiskCheckResult` | Spec 10 | Phase 3 only (`risk_enabled`) |
| `correlation_id` | Spec 20 Pipeline | Yes |

## Outputs

| Output | Type | Consumers |
|--------|------|-----------|
| `TradingDecision` | Domain model | Journal (13), Execution (11), Frontend (21) |
| `decision.emitted` | Domain event | AI (15), Analytics (14), WebSocket |

## Interfaces

```python
class DecisionEngineServiceProtocol(Protocol):
    def resolve(
        self,
        confluence: ConfluenceResult,
        validation: ValidationResult,
        news_status: NewsFilterStatus,
        strategy: StrategyProfile,
        risk: RiskCheckResult | None,
        correlation_id: str,
    ) -> TradingDecision: ...
```

## Database

| Table / Cache | Operation | Owner |
|---------------|-----------|-------|
| `decisions` | INSERT (immutable) | This spec |
| `decision:{symbol}:latest` | Redis cache (TTL 30s) | This spec |

## Decision Logic

Priority order (deterministic):

1. News Filter `is_blocked` → WAIT
2. Validation `is_valid == False` → WAIT
3. Confluence score < `strategy.min_confluence_score` → WAIT
4. Direction not in `strategy.enabled_directions` → WAIT
5. If `risk_enabled` and risk breached → WAIT
6. Confluence `suggested_direction == WAIT` → WAIT
7. Otherwise → actionable BUY or SELL

```python
def resolve_decision(...) -> TradingDecision:
    if news_status.is_blocked:
        return wait("High-impact news window active")
    if not validation.is_valid:
        return wait("Validation failed", validation.failed_rules)
    if confluence.total_score < strategy.min_confluence_score:
        return wait("Confluence below threshold")
    if not strategy.is_direction_enabled(confluence.suggested_direction):
        return wait("Direction disabled by strategy profile")
    if risk is not None and not risk.within_limits:
        return wait("Risk limits breached", risk.breach_reason)
    if confluence.suggested_direction == Direction.WAIT:
        return wait("Insufficient evidence")
    return actionable(confluence.suggested_direction, ...)
```

### Analysis MVP Mode (`risk_enabled: false`)

Phase 1 emits actionable BUY/SELL from confluence + validation only. `risk_snapshot = null`. Execution Engine inactive.

### Soft News Downgrade

Handled upstream in Confluence (score penalty). Decision Engine only checks hard `is_blocked`.

## Domain Models

```python
@dataclass(frozen=True)
class TradingDecision:
    id: UUID
    instrument: Instrument
    direction: Direction
    is_actionable: bool
    confluence_score: Decimal
    confluence_snapshot: ConfluenceResult
    validation_snapshot: ValidationResult
    risk_snapshot: RiskParameters | None
    strategy_id: str
    news_status: NewsFilterStatus
    reason: str
    correlation_id: str
    decided_at: datetime
```

## Edge Cases

| Case | Behavior |
|------|----------|
| Duplicate pipeline run same bar | Deduped by pipeline (Spec 20); no double insert |
| All WAIT conditions false but direction WAIT | WAIT with reason "Insufficient evidence" |
| Risk skipped (`risk_enabled: false`) | `risk_snapshot = null`; steps 5 skipped |
| DB insert fails | Log error; still publish event (or use outbox) |

## Acceptance Criteria

- [ ] WAIT for every blocking condition
- [ ] Every decision persisted with full snapshots
- [ ] `decision.emitted` for all decisions including WAIT
- [ ] Deterministic: same inputs → same output
- [ ] REST and WebSocket expose latest
- [ ] Unit test per decision branch
- [ ] Integration test: pipeline bar → decision

## Dependencies

- Spec 08, 09, 18, 19, 20
- Spec 10 (Phase 3, optional)

## Downstream Consumers

- AI Explanation (15), Journal (13), Execution (11), Frontend (21)
