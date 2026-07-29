# ATLAS Coding Standards

## Language & Style

- **Python 3.11+** for backend
- **TypeScript** for frontend
- Follow **PEP 8**; use **Ruff** for linting and formatting
- Maximum line length: 100 characters
- Use **type hints** on all public functions, methods, and module-level variables where applicable

## Documentation

- Every public module, class, and function requires a **docstring**
- Docstrings use Google style
- Non-obvious business logic requires inline comments explaining *why*, not *what*

## Architecture Rules

- **Dependency injection** for all services; no module-level singletons for business logic
- **No global mutable state**
- Domain layer must not import from infrastructure or presentation
- Use **interfaces (Protocol / ABC)** at module boundaries
- Prefer **composition** over inheritance

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Modules | snake_case | `trade_validation.py` |
| Classes | PascalCase | `TradeValidator` |
| Functions / methods | snake_case | `calculate_position_size` |
| Constants | UPPER_SNAKE_CASE | `MAX_RISK_PERCENT` |
| Domain events | PascalCase + Event suffix | `TradeValidatedEvent` |
| Interfaces | PascalCase + suffix | `IMarketDataProvider` or `MarketDataProviderProtocol` |

## Error Handling

- Use domain-specific exception types; never swallow exceptions silently
- Log errors with structured context (module, correlation_id, instrument, timeframe)
- API layer maps domain exceptions to appropriate HTTP status codes
- Fail closed on validation and risk checks

## Logging

- Structured JSON logging in production
- Log levels: DEBUG (dev only), INFO (lifecycle events), WARNING (degraded state), ERROR (failures)
- Never log secrets, tokens, or full account credentials

## Testing Requirements

Every new feature must include:

| Test Type | Scope |
|-----------|-------|
| **Unit tests** | Domain logic, validators, calculators — no I/O |
| **Integration tests** | Database, Redis, API endpoints with test containers |
| **Contract tests** | External data provider adapters (where applicable) |

- Use **pytest** and **pytest-asyncio** for async code
- Test file naming: `test_<module>.py`
- Aim for meaningful coverage of business rules, not arbitrary percentage targets
- Do not add tests that only assert trivial getters/setters

## Accuracy Requirements

All analysis modules must follow [Accuracy Principles](accuracy_principles.md):

- Deterministic rules defined in specs before implementation
- Golden tests: same input bars → same output
- No look-ahead in live or backtest paths
- Indicators and patterns are evidence, never standalone signals

## Feature Checklist

Each new feature or module must deliver:

- [ ] Domain models (entities / value objects)
- [ ] Interfaces (ports)
- [ ] Application services / use cases
- [ ] Infrastructure adapters (if needed)
- [ ] Dependency injection registration
- [ ] Unit tests
- [ ] Integration tests (where appropriate)
- [ ] Structured logging
- [ ] Error handling
- [ ] Documentation update in `docs/` or relevant spec

## Git & Code Review

- One module per feature branch when possible
- Commits are atomic and describe *why*
- No unrelated refactors in feature PRs
- All CI checks must pass before merge
