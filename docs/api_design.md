# ATLAS API Design

## Principles

- REST for request/response operations; WebSockets for realtime streams
- Controllers are thin — delegate to application use cases immediately
- No trading logic in route handlers
- All responses use consistent envelope shapes
- OpenAPI documentation generated automatically via FastAPI

## Base URL

```
/api/v1
```

## Authentication

- JWT Bearer token in `Authorization` header
- Refresh token via `POST /api/v1/auth/refresh`
- Public endpoints: health check, login, register (if enabled)

## Standard Response Envelope

```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-07-29T08:30:00Z"
  }
}
```

Error responses:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Human-readable message",
    "details": []
  },
  "meta": { "request_id": "uuid", "timestamp": "..." }
}
```

## Core REST Endpoints (Planned)

### Health & System

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/ready` | Readiness (DB, Redis) |

### Market Data

| Method | Path | Description |
|--------|------|-------------|
| GET | `/instruments` | List supported instruments |
| GET | `/market-data/{symbol}/bars` | Historical OHLCV |
| GET | `/market-data/{symbol}/latest` | Latest bar / tick |

### Analysis & Decisions

| Method | Path | Description |
|--------|------|-------------|
| GET | `/analysis/{symbol}/context` | Current market context snapshot |
| GET | `/analysis/{symbol}/confluence` | Confluence score breakdown |
| GET | `/decisions/{symbol}/latest` | Latest BUY/SELL/WAIT decision |
| GET | `/decisions/{symbol}/history` | Decision audit trail |
| GET | `/pipeline/{symbol}/latest` | Last pipeline run status and timing |

### Strategy & News

| Method | Path | Description |
|--------|------|-------------|
| GET | `/strategy/profiles` | List strategy profiles |
| GET | `/strategy/active` | Active strategy profile |
| PUT | `/strategy/active` | Switch active profile |
| GET | `/news/upcoming` | Upcoming economic events |
| GET | `/news/status` | Current news filter status |

### Trades & Journal

| Method | Path | Description |
|--------|------|-------------|
| GET | `/trades` | List trades (filtered, paginated) |
| GET | `/trades/{id}` | Trade detail with full audit |
| POST | `/trades/{id}/notes` | Add trader notes |

### Risk & Positions

| Method | Path | Description |
|--------|------|-------------|
| GET | `/positions/open` | Open positions |
| GET | `/risk/profile` | Current risk settings |
| PUT | `/risk/profile` | Update risk parameters |

### Analytics

| Method | Path | Description |
|--------|------|-------------|
| GET | `/analytics/summary` | Trade performance summary |
| GET | `/analytics/equity-curve` | Equity curve data |
| GET | `/analytics/decisions` | Decision stats (WAIT rate, reasons) |
| GET | `/analytics/modules` | Module accuracy breakdown |

## WebSocket Channels

Connect: `ws://host/api/v1/ws?token=<jwt>`

| Channel | Payload | Description |
|---------|---------|-------------|
| `market.{symbol}.bars` | OHLCV bar updates | Live candle stream |
| `decisions.{symbol}` | Decision events | BUY/SELL/WAIT changes |
| `positions` | Position updates | Open/close/modify events |
| `system.alerts` | System notifications | Errors, news blocks |

### WebSocket Message Format

```json
{
  "channel": "decisions.XAUUSD",
  "event": "decision.updated",
  "payload": {},
  "timestamp": "2026-07-29T08:30:00Z"
}
```

## Versioning

- URL path versioning: `/api/v1`
- Breaking changes require `/api/v2`; v1 maintained until deprecation window ends

## Rate Limiting

- Redis-backed rate limits per user/IP
- Stricter limits on analysis endpoints that trigger heavy computation

## Pagination

Query params: `page`, `page_size` (max 100), `sort`, `order`

```json
{
  "data": [],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 150
  }
}
```
