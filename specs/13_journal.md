# Spec 13 — Trading Journal

## Objective

Immutable record of every decision and trade lifecycle event.

## Scope

### In Scope

- Event handlers for decisions and trades
- Full snapshot persistence
- Trader notes (Phase 3)
- REST history endpoints

### Out of Scope

- Screenshot upload, social sharing

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| `decision.emitted` | Spec 17 | Phase 1 |
| `validation.completed` | Spec 09 | Optional enrich |
| `trade.*` events | Specs 11, 12 | Phase 3 |
| Trader note payload | REST POST | Phase 3 |

## Outputs

| Output | Type | Consumers |
|--------|------|-----------|
| `decisions` rows | DB (via Spec 17 primary write; journal may duplicate for search) | Analytics (14) |
| `journal_entries` | DB notes | Frontend (21) |
| `trade_events` | Append-only | Analytics (14) |

## Interfaces

```python
class JournalServiceProtocol(Protocol):
    async def on_decision(self, decision: TradingDecision) -> None: ...
    async def on_trade_event(self, event: TradeLifecycleEvent) -> None: ...
    async def add_note(self, trade_id: UUID, content: str, tags: list[str]) -> JournalEntry: ...
    async def query_decisions(self, filters: DecisionFilters) -> PaginatedResult: ...
```

## Database

| Table / Cache | Operation | Owner |
|---------------|-----------|-------|
| `decisions` | INSERT (primary: Spec 17; journal indexes for query) | Spec 17 |
| `journal_entries` | INSERT notes/tags | This spec |
| `trade_events` | INSERT append-only | Specs 11, 12 |

**Storage mapping:**

| Data | Table | Phase |
|------|-------|-------|
| Decision + snapshots | `decisions` | 1 |
| Trader notes | `journal_entries` | 3 |
| Trade lifecycle | `trade_events` | 3 |
| Trade header | `trades` | 3 |

## Phase Delivery

**Phase 1:** `on_decision` handler — all WAIT included.  
**Phase 3:** Trade events + notes.

## Domain Models

```python
@dataclass(frozen=True)
class JournalEntry:
    id: UUID
    decision_id: UUID | None
    trade_id: UUID | None
    user_id: UUID
    entry_type: str
    content: str
    tags: list[str]
    created_at: datetime
```

## Edge Cases

| Case | Behavior |
|------|----------|
| Duplicate `decision.emitted` | Idempotent insert by `decision.id` |
| Out-of-order trade events | Process by `created_at`; reject if trade not found |
| Note on non-existent trade | 404 |

## Acceptance Criteria

### Phase 1
- [ ] Every decision persisted with snapshots
- [ ] WAIT included; correlation ID searchable
- [ ] Paginated history with filters

### Phase 3
- [ ] Trade lifecycle append-only
- [ ] Notes and tags
- [ ] Integration test full lifecycle

## Dependencies

- Spec 17 (Phase 1), Specs 11–12 (Phase 3)

## Downstream Consumers

- Analytics (14), AI (15), Frontend (21)
