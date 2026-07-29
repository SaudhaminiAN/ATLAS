# ATLAS Deployment

## Overview

Version 1 deploys as a **Docker Compose** stack suitable for local development and single-server production. No Kubernetes requirement for v1.

## Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `api` | Custom (backend Dockerfile) | 8000 | FastAPI application |
| `frontend` | Custom (frontend Dockerfile) | 3000 | React dev / Nginx prod |
| `postgres` | postgres:16-alpine | 5432 | Primary database |
| `redis` | redis:7-alpine | 6379 | Cache and pub/sub |

## Directory Layout

```
docker/
├── docker-compose.yml
├── docker-compose.prod.yml
├── backend.Dockerfile
├── frontend.Dockerfile
└── nginx/
    └── nginx.conf
```

## Local Development

```bash
docker compose -f docker/docker-compose.yml up -d
```

Backend hot-reload mounts `backend/src` as a volume.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis connection string |
| `JWT_SECRET` | Yes | Signing key for JWT |
| `JWT_ACCESS_EXPIRE_MINUTES` | No | Default: 30 |
| `JWT_REFRESH_EXPIRE_DAYS` | No | Default: 7 |
| `LOG_LEVEL` | No | Default: INFO |
| `MARKET_DATA_API_KEY` | Yes (prod) | External data provider key |
| `LLM_API_KEY` | Yes (prod) | AI Explanation provider key |

Secrets are injected via environment or secret manager — never committed to source control.

## Production Checklist

- [ ] Use `docker-compose.prod.yml` overrides
- [ ] Enable HTTPS via reverse proxy (Nginx / Caddy)
- [ ] Set strong `JWT_SECRET` (256-bit random)
- [ ] Configure PostgreSQL backups
- [ ] Set resource limits on containers
- [ ] Enable structured JSON logging
- [ ] Configure health check endpoints for orchestrator
- [ ] Restrict CORS to known frontend origins

## Health Checks

- **Liveness:** `GET /api/v1/health` — process is running
- **Readiness:** `GET /api/v1/ready` — DB and Redis reachable

## Scaling Notes (v1)

- Single API instance is sufficient for v1
- Horizontal scaling requires Redis pub/sub for WebSocket fan-out (already planned)
- PostgreSQL read replicas not required for v1

## CI/CD (Planned)

GitHub Actions pipeline:

1. Lint (Ruff, ESLint)
2. Unit tests (pytest)
3. Integration tests (testcontainers)
4. Build Docker images
5. Push to registry
6. Deploy via Compose or manual pull
