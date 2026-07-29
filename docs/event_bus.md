# ATLAS Event Bus

## Purpose

The internal event bus decouples domain modules within the modular monolith. Modules publish domain events; other modules subscribe without direct imports.

This is **not** a distributed message broker in v1. It is an in-process pub/sub mechanism with optional Redis pub/sub for WebSocket fan-out.

## Design

```
Publisher (Domain Service)
        │
        ▼
   Event Bus (in-process)
        │
        ├──▶ Handler A (e.g. Journal)
        ├──▶ Handler B (e.g. Analytics)
        └──▶ Handler C (e.g. WebSocket Bridge)
```

## Event Naming Convention

```
<domain>.<entity>.<action>
```

## Event Structure

```python
@dataclass(frozen=True)
class DomainEvent:
    event_id: UUID
    event_type: str
    occurred_at: datetime
    correlation_id: str
    payload: dict[str, Any]
```

All events are **immutable** (`frozen=True` dataclasses or Pydantic models with `frozen=True`).

Every event in the analysis pipeline carries the same `correlation_id` for end-to-end tracing.

## Core Domain Events

| Event | Publisher | Subscribers |
|-------|-----------|-------------|
| `market_data.bar.received` | Market Data | Analysis Pipeline |
| `market_data.gap.detected` | Market Data | Logging, Alerts |
| `market_context.updated` | Market Context | Confluence |
| `analysis.mtf.completed` | MTF Analysis | Confluence |
| `analysis.technical.completed` | Technical Analysis | Confluence |
| `analysis.smc.completed` | SMC | Confluence, Price Action |
| `analysis.price_action.completed` | Price Action | Confluence |
| `news.window.blocked` | News Filter | Validation, Decision Engine |
| `news.window.cleared` | News Filter | Validation, Decision Engine |
| `confluence.calculated` | Confluence | Validation |
| `validation.completed` | Trade Validation | Decision Engine, Journal |
| `risk.calculated` | Risk Management | Decision Engine |
| `risk.limit.breached` | Risk Management | Decision Engine, Alerts |
| `decision.emitted` | Decision Engine | AI Explanation, Journal, Analytics, WebSocket |
| `strategy.profile.changed` | Strategy Engine | Confluence, Validation, Pipeline |
| `pipeline.completed` | Analysis Pipeline | Logging, Frontend |
| `pipeline.failed` | Analysis Pipeline | Logging, Alerts |
| `trade.opened` | Execution Engine | Position Management, Journal |
| `trade.closed` | Position Management | Analytics, Journal |

## Handler Rules

- Handlers are idempotent where possible
- Handlers must not raise unhandled exceptions — log and continue
- Handlers run synchronously in v1
- Handlers must not call back into the publisher synchronously (avoid circular calls)

## Interface

```python
class EventBusProtocol(Protocol):
    def publish(self, event: DomainEvent) -> None: ...
    def subscribe(self, event_type: str, handler: EventHandler) -> None: ...
    def unsubscribe(self, event_type: str, handler: EventHandler) -> None: ...
```

## WebSocket Bridge

Subscribes to `decision.emitted`, `market_data.bar.received`, and trade events; pushes to WebSocket clients via Redis pub/sub.

## Testing

- Unit tests: mock event bus, assert publish calls
- Integration tests: subscribe handler, publish event, assert side effects
- Pipeline tests: assert same `correlation_id` across all stage events

## Future Considerations

- Outbox pattern for reliable external delivery
- Celery/ARQ for async heavy handlers
- Event replay for backtesting module
