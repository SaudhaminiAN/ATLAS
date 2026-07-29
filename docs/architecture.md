# ATLAS Architecture

## Overview

ATLAS follows a **Modular Monolith** with **Clean Architecture**, **Domain-Driven Design (DDD)**, and **SOLID** principles. Version 1 does not use microservices.

```
┌─────────────────────────────────────────────────────────────┐
│                      Presentation Layer                      │
│              FastAPI (REST + WebSockets) · React             │
├─────────────────────────────────────────────────────────────┤
│                    Application Layer                         │
│    Analysis Pipeline · Use Cases · Event Handlers            │
├─────────────────────────────────────────────────────────────┤
│                      Domain Layer                            │
│    Entities · Value Objects · Domain Services · Events       │
├─────────────────────────────────────────────────────────────┤
│                   Infrastructure Layer                       │
│   PostgreSQL · Redis · Market Data Providers · Brokers       │
└─────────────────────────────────────────────────────────────┘
```

Dependencies point **inward**. Domain knows nothing about infrastructure.

## Analysis Pipeline

All live and backtest analysis flows through a single orchestrator (Spec 20):

```
Bar Close → Context → MTF → TA ∥ SMC → PA → News → Confluence
         → Validation → Risk → Decision Engine → Journal
```

See `specs/20_analysis_pipeline.md` and `docs/accuracy_principles.md`.

## Layer Responsibilities

| Layer | Responsibility |
|-------|----------------|
| **Domain** | Business rules, entities, value objects, domain events, interfaces (ports) |
| **Application** | Pipeline orchestration, use cases, transaction boundaries, event publishing |
| **Infrastructure** | Database, cache, external APIs, message adapters |
| **Presentation** | HTTP/WebSocket handlers; no trading logic in controllers |

## Domain Modules

Modules communicate through **interfaces** and **domain events**. Each module has a corresponding spec.

| Module | Spec | Purpose |
|--------|------|---------|
| Market Data | 02 | Ingest, validate, stream OHLCV |
| Market Context | 03 | Session, volatility, structural bias |
| Multi-Timeframe Analysis | 04 | Align bias across timeframes |
| Technical Analysis | 05 | S/R, trend, indicator context |
| Smart Money Concepts | 06 | BOS/CHoCH, OB, liquidity, FVG |
| Price Action | 07 | Candle patterns at key levels |
| Confluence | 08 | Weighted evidence aggregation |
| Trade Validation | 09 | Deterministic pass/fail rules |
| Risk Management | 10 | Position sizing, SL/TP, limits |
| Execution Engine | 11 | Order placement and fills |
| Position Management | 12 | Breakeven, trailing, partial exits |
| Trading Journal | 13 | Decision and trade records |
| Analytics | 14 | Performance and module accuracy |
| AI Explanation | 15 | Natural-language summaries |
| Backtesting | 16 | Historical pipeline replay |
| Decision Engine | 17 | Final BUY / SELL / WAIT authority |
| Strategy Engine | 18 | Configurable profiles and weights |
| News Filter | 19 | High-impact event blocking |
| Analysis Pipeline | 20 | End-to-end orchestration |
| Frontend | 21 | Analysis dashboard UI |

## Cross-Cutting Concerns

- **Dependency Injection** — constructor injection via a container; no global state
- **Event Bus** — internal pub/sub (see `event_bus.md`)
- **Structured Logging** — JSON logs with correlation IDs
- **Configuration** — environment-based settings; secrets outside source control
- **Accuracy** — deterministic rules, no look-ahead, measurable outcomes (see `accuracy_principles.md`)

## Backend Directory Layout

```
backend/
├── src/
│   └── atlas/
│       ├── domain/
│       ├── application/
│       │   └── pipeline/       # AnalysisPipelineOrchestrator
│       ├── infrastructure/
│       └── presentation/
├── alembic/
├── tests/
├── pyproject.toml
└── Dockerfile
```

## Key Design Rules

- Composition over inheritance
- Small, focused classes and functions
- Trading logic never lives in API controllers
- One major module implemented at a time
- Same pipeline code for live and backtest
- Preserve backward compatibility when extending

## Implementation Phases

See `docs/mvp_roadmap.md`:

1. **Phase 1** — Analysis MVP (Specs 01–09, 17–21 partial)
2. **Phase 2** — Measure accuracy (Specs 14, 16, 21 Phase 2)
3. **Phase 3** — Execution & AI (Specs 10–12, 15)
4. **Phase 4** — Production hardening

## Instrument Extensibility

Core domain types (`Instrument`, `Symbol`, `Timeframe`) are instrument-agnostic. XAUUSD-specific constants live in configuration or strategy modules, not in shared kernel types.
