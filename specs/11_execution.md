# Spec 11 — Execution Engine

## Objective

Place and track orders for **actionable** decisions. Paper trading default.

## Scope

### In Scope

- `IExecutionProvider` port + paper executor
- Order lifecycle management
- Idempotent submission
- `ExecutionService`
- Events: `trade.opened`, `trade.rejected`, `trade.cancelled`
- REST trade endpoints

### Out of Scope

- Live broker (gated), partial fills, mid-flight modification

## Phase Note

**Phase 3.** Subscribes to `decision.emitted` where `is_actionable = True`.

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| `TradingDecision` (`is_actionable=True`) | Spec 17 event | Yes |
| `RiskParameters` | Decision `risk_snapshot` | Yes |
| `idempotency_key` | `decision.id` | Yes |

## Outputs

| Output | Type | Consumers |
|--------|------|-----------|
| `OrderResult` | Domain model | Position Mgmt (12) |
| `Trade` record | DB | Journal (13), Analytics (14) |
| `trade.opened` etc. | Events | Specs 12, 13 |

## Interfaces

```python
class IExecutionProvider(Protocol):
    async def submit_order(self, request: OrderRequest) -> OrderResult: ...
    async def cancel_order(self, order_id: str) -> OrderResult: ...

class ExecutionServiceProtocol(Protocol):
    async def on_decision(self, decision: TradingDecision) -> OrderResult | None: ...
```

## Database

| Table / Cache | Operation | Owner |
|---------------|-----------|-------|
| `trades` | INSERT, UPDATE status | This spec |
| `trade_events` | INSERT append-only | This spec |
| `execution:idem:{key}` | Redis NX (TTL 300s) | This spec |

## Edge Cases

| Case | Behavior |
|------|----------|
| `is_actionable = False` | Skip silently |
| Duplicate idempotency key | Return existing result |
| Paper slippage | `fill = entry ± slippage` |
| Provider timeout | `trade.rejected`, log error |
| `EXECUTION_MODE != live` | Paper only |

## Acceptance Criteria

- [ ] Actionable decisions only
- [ ] Idempotency enforced
- [ ] Paper fill with slippage
- [ ] Audit trail in `trades` + `trade_events`
- [ ] Live mode gated

## Dependencies

- Spec 10, 17

## Downstream Consumers

- Position Management (12), Journal (13)
