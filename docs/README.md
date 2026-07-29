# ATLAS Documentation

Core project documentation for **Project ATLAS** — an institutional-grade AI-powered trading analysis platform for XAUUSD.

## Document Index

| Document | Description |
|----------|-------------|
| [vision.md](vision.md) | Project goals, trading philosophy, AI constraints |
| [architecture.md](architecture.md) | System design, layers, modules, pipeline |
| [coding_standards.md](coding_standards.md) | Engineering conventions, testing, naming |
| [technology_stack.md](technology_stack.md) | Languages, frameworks, tools, integrations |
| [api_design.md](api_design.md) | REST endpoints, WebSocket channels, envelopes |
| [database_design.md](database_design.md) | PostgreSQL schema, Redis keys, migrations |
| [deployment.md](deployment.md) | Docker Compose, env vars, CI/CD, health checks |
| [security.md](security.md) | Auth, secrets, trading safety, audit |
| [event_bus.md](event_bus.md) | Internal events, naming, handler rules |

## Supplementary Documents

| Document | Description |
|----------|-------------|
| [accuracy_principles.md](accuracy_principles.md) | What "accurate" means; deterministic rules |
| [mvp_roadmap.md](mvp_roadmap.md) | Phased implementation plan |

## Reading Order

**New to the project:**

1. `vision.md` — understand the why
2. `architecture.md` — understand the how
3. `mvp_roadmap.md` — understand build order

**Before implementing a module:**

1. Relevant spec in `../specs/`
2. `coding_standards.md`
3. `api_design.md` / `database_design.md` (if touching API or DB)
4. `event_bus.md` (if publishing or subscribing to events)

**Before deploying:**

1. `deployment.md`
2. `security.md`

## Related

- Module specifications: [`../specs/`](../specs/)
- Project README: [`../README.md`](../README.md)
