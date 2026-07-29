# ATLAS Technology Stack

## Backend

| Component | Technology | Purpose |
|-----------|------------|---------|
| Language | Python 3.11+ | Core business logic |
| Framework | FastAPI | REST API and WebSocket server |
| ASGI Server | Uvicorn | Production HTTP/WebSocket serving |
| Validation | Pydantic v2 | Request/response and settings models |
| ORM | SQLAlchemy 2.x (async) | PostgreSQL persistence |
| Migrations | Alembic | Schema versioning |
| Task Queue | (Future) Celery / ARQ | Background jobs if needed |
| Testing | pytest, pytest-asyncio, httpx | Unit and integration tests |

## Frontend

| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | React 18+ | UI |
| Language | TypeScript | Type-safe components |
| Styling | Tailwind CSS | Utility-first styling |
| Build | Vite | Dev server and bundling |
| State | (TBD) Zustand or React Query | Client state and server cache |
| Charts | (TBD) Lightweight Charts | Price and analytics visualization |

## Data & Cache

| Component | Technology | Purpose |
|-----------|------------|---------|
| Primary DB | PostgreSQL 16 | Trades, journal, users, config |
| Cache | Redis 7 | Session cache, rate limits, pub/sub |
| Time-series | PostgreSQL (v1) | OHLCV bars; dedicated TSDB optional later |

## Realtime

| Component | Technology | Purpose |
|-----------|------------|---------|
| Protocol | WebSockets (FastAPI) | Live prices, decisions, position updates |
| Internal | Domain Event Bus | Module-to-module decoupling |

## Authentication

| Component | Technology | Purpose |
|-----------|------------|---------|
| Auth | JWT (access + refresh) | Stateless API authentication |
| Hashing | bcrypt / passlib | Password storage |

## DevOps

| Component | Technology | Purpose |
|-----------|------------|---------|
| Containers | Docker + Docker Compose | Local and production deployment |
| CI | GitHub Actions (planned) | Lint, test, build |
| Logging | structlog | Structured application logs |
| Monitoring | (Future) Prometheus + Grafana | Metrics and alerting |

## External Integrations (Planned)

| Integration | Purpose |
|-------------|---------|
| Market data provider | Live and historical XAUUSD OHLCV |
| Broker API | Order execution (Execution Engine) |
| Economic calendar API | News Filter module |
| LLM provider | AI Explanation module (read-only context) |

## Version 1 Constraints

- Single instrument: XAUUSD
- Modular monolith — no microservices
- No Kubernetes requirement for v1; Docker Compose is sufficient
