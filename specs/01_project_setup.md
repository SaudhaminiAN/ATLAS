# Spec 01 — Project Setup

## Objective

Establish the ATLAS monorepo foundation: backend, frontend, Docker, CI, and shared domain kernel.

## Scope

### In Scope

- Repository structure per architecture doc
- FastAPI + DI + structured logging
- React + TypeScript + Tailwind scaffold
- Docker Compose (PostgreSQL, Redis, API, frontend)
- Alembic, health/ready endpoints
- Base domain types, event bus, pipeline stub
- pytest, `.env.example`, `.gitignore`

### Out of Scope

- Market data, trading logic, full auth, production hardening

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Environment variables | `.env` | Yes |
| Docker / Python 3.11+ / Node 20+ | Host | Yes |

## Outputs

| Output | Type | Consumers |
|--------|------|-----------|
| Running API | HTTP :8000 | All backend specs |
| Running frontend | HTTP :3000 | Spec 21 |
| PostgreSQL + Redis | Infrastructure | All specs |
| Domain kernel types | Python package | All specs |
| `EventBusProtocol` + impl | Python package | All specs |

## Interfaces

```python
class EventBusProtocol(Protocol):
    def publish(self, event: DomainEvent) -> None: ...
    def subscribe(self, event_type: str, handler: EventHandler) -> None: ...
    def unsubscribe(self, event_type: str, handler: EventHandler) -> None: ...

@dataclass(frozen=True)
class DomainEvent:
    event_id: UUID
    event_type: str
    occurred_at: datetime
    correlation_id: str
    payload: dict[str, Any]
```

Kernel types: `Instrument`, `Timeframe`, `Direction`, `Bias`, `Money`, `Price`, `TradingSession`, `VolatilityRegime`.

## Database

| Table / Cache | Operation | Owner |
|---------------|-----------|-------|
| `instruments` | Seed XAUUSD | Initial migration |
| `strategy_profiles` | Seed default profile | Initial migration |
| Alembic | Migration framework | This spec |

Initial migration only — full schema added per module specs.

## Edge Cases

| Case | Behavior |
|------|----------|
| PostgreSQL unreachable | `/ready` returns 503 |
| Redis unreachable | `/ready` returns 503 |
| Missing `JWT_SECRET` | Fail startup with clear error |
| Docker port conflict | Document in README |

## Deliverables

See directory tree in original spec (backend/, frontend/, docker/).

## Acceptance Criteria

- [ ] `docker compose up` starts all services
- [ ] `GET /api/v1/health` → 200
- [ ] `GET /api/v1/ready` checks DB + Redis
- [ ] `pytest` passes (≥1 test)
- [ ] Frontend loads at :3000
- [ ] Alembic initial migration runs
- [ ] Structured JSON logs on startup
- [ ] `EventBusProtocol` unit test

## Dependencies

None.

## Implementation Order

1. Backend structure + pyproject.toml
2. Domain kernel + event bus
3. FastAPI + DI
4. PostgreSQL + Redis adapters
5. Docker Compose
6. Frontend Vite scaffold
7. CI skeleton
