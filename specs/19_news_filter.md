# Spec 19 — News Filter

## Objective

Block or downgrade decisions during high-impact economic events affecting XAUUSD.

## Scope

### In Scope

- `INewsCalendarProvider` + mock
- Hard block and soft downgrade windows
- `NewsFilterService`
- REST status endpoints

### Out of Scope

- Sentiment analysis, auto geopolitical detection

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Economic calendar | `INewsCalendarProvider` | Yes |
| Current UTC time | System clock | Yes |
| `trigger_bar.open_time` | Pipeline | Yes (use bar time, not wall clock in backtest) |

## Outputs

| Output | Type | Consumers |
|--------|------|-----------|
| `NewsFilterStatus` | Domain model | Confluence (08), Validation (09), Decision (17) |
| `news.window.blocked/cleared` | Events | Alerts |

## Interfaces

```python
class INewsCalendarProvider(Protocol):
    async def fetch_upcoming(
        self, start: datetime, end: datetime
    ) -> list[EconomicEvent]: ...

class NewsFilterServiceProtocol(Protocol):
    def check(self, as_of: datetime) -> NewsFilterStatus: ...
```

## Database

| Table / Cache | Operation | Owner |
|---------------|-----------|-------|
| `economic_events` | INSERT/SELECT (synced from provider) | This spec |
| `news:events:upcoming` | Redis cache (TTL 900s) | This spec |

## Configuration

```yaml
news_filter:
  hard_block_minutes_before: 15
  hard_block_minutes_after: 15
  soft_downgrade_minutes_before: 30
  soft_downgrade_minutes_after: 30
  soft_downgrade_penalty: 0.20
```

## Edge Cases

| Case | Behavior |
|------|----------|
| Overlapping events | Union of windows; worst case wins (block > downgrade) |
| Event timezone | Normalize all `scheduled_at` to UTC at ingest |
| Calendar stale | Refresh every 15 min; if stale >1h log warning |
| Backtest | Use `as_of = bar.open_time`, not wall clock |
| Medium/low impact | Ignored in v1 (high only) |

## Acceptance Criteria

- [ ] Hard block within ±15 min (configurable)
- [ ] Soft penalty within ±30 min
- [ ] Overlapping events tested
- [ ] UTC normalization
- [ ] Mock provider for CI
- [ ] Boundary tests before/during/after

## Dependencies

- Spec 01

## Downstream Consumers

- Confluence (08), Validation (09), Decision Engine (17)
