# ATLAS Security

## Authentication

- **JWT** access tokens (short-lived) and refresh tokens (long-lived, rotatable)
- Access token in `Authorization: Bearer <token>` header
- Refresh tokens stored in httpOnly secure cookies (frontend) or secure client storage
- Passwords hashed with bcrypt (cost factor ≥ 12)

## Authorization

- Role-based access control (RBAC) planned for v2
- v1: authenticated users access their own trades, journal, and risk profile
- Admin endpoints protected by separate role flag

## API Security

- HTTPS enforced in production
- CORS restricted to configured frontend origins
- Rate limiting via Redis (per user and per IP)
- Request size limits on upload endpoints
- Input validation via Pydantic on all endpoints

## Secrets Management

- No secrets in source control or Docker images
- Environment variables or secret manager (e.g. Docker secrets, AWS SSM) in production
- `.env` files gitignored; `.env.example` documents required variables without values

## Data Protection

- PostgreSQL connections use TLS in production
- Sensitive fields (password hashes) never returned in API responses
- Trade and decision audit logs are append-only
- User data export and deletion workflows planned for compliance

## Trading Safety

- AI layer cannot override deterministic validation or risk limits
- Risk Management module enforces hard caps regardless of confluence score
- Execution Engine requires explicit configuration to enable live trading (paper mode default)
- All order submissions logged with full audit trail

## Dependency Security

- Pin dependencies in `pyproject.toml` and `package.json`
- Regular dependency audits (`pip audit`, `npm audit`)
- CI fails on known critical vulnerabilities

## Logging & Audit

- Structured logs include `correlation_id` but exclude credentials
- Authentication failures logged with IP (not password)
- Decision and trade events fully auditable in database

## WebSocket Security

- JWT required on WebSocket handshake
- Channel subscriptions validated against user permissions
- Heartbeat / timeout to detect stale connections

## Incident Response

- Log aggregation for error alerting (planned)
- Ability to disable live execution via feature flag / environment variable
- Database backups for recovery
