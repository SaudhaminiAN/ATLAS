# ATLAS

Institutional-grade AI-powered decision support system for **XAUUSD (Gold)** trading.

## Overview

ATLAS analyzes live market data using Technical Analysis, Smart Money Concepts, and Price Action to detect high-probability trading opportunities. It applies deterministic validation rules, manages risk automatically, and explains every decision — defaulting to **WAIT** when evidence is insufficient.

## License

Proprietary — All rights reserved.

## Documentation

Core docs live in [`docs/`](docs/):

| Document | Purpose |
|----------|---------|
| [vision.md](docs/vision.md) | Goals and trading philosophy |
| [architecture.md](docs/architecture.md) | System design |
| [coding_standards.md](docs/coding_standards.md) | Engineering conventions |
| [technology_stack.md](docs/technology_stack.md) | Stack and tools |
| [api_design.md](docs/api_design.md) | REST and WebSocket API |
| [database_design.md](docs/database_design.md) | Schema design |
| [deployment.md](docs/deployment.md) | Docker and deployment |
| [security.md](docs/security.md) | Auth and safety |
| [event_bus.md](docs/event_bus.md) | Internal events |

See [docs/README.md](docs/README.md) for the full index.

## Module Specifications (21 specs)

```
Phase 1 — Analysis MVP
  01 Project Setup          18 Strategy Engine
  02 Market Data            19 News Filter
  03 Market Context         20 Analysis Pipeline
  04 Multi-TF Analysis      21 Frontend
  05 Technical Analysis
  06 SMC
  07 Price Action
  08 Confluence
  09 Validation
  17 Decision Engine

Phase 2 — Measure Accuracy
  14 Analytics              16 Backtesting

Phase 3 — Execution & AI
  10 Risk                   13 Journal
  11 Execution              15 AI Explanation
  12 Position Management
```

See [MVP Roadmap](docs/mvp_roadmap.md) for implementation order.

## Project Structure

```
ATLAS/
├── docs/          Architecture and design documentation
├── specs/         Module implementation specifications (01–21)
├── backend/       Python / FastAPI application
├── frontend/      React / TypeScript application
├── tests/         Cross-cutting integration tests
└── docker/        Docker Compose and container configs
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop

### Quick start (Docker)

```bash
cp .env.example .env
# Edit JWT_SECRET in .env (min 16 characters)

docker compose -f docker/docker-compose.yml up --build
```

| Service | URL |
|---------|-----|
| API | http://localhost:8000/api/v1/docs |
| Health | http://localhost:8000/api/v1/health |
| Frontend | http://localhost:3000 |

### Local backend (without Docker)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
set JWT_SECRET=dev-secret-min-16-chars
uvicorn atlas.presentation.api.main:app --reload --app-dir src
pytest
```

### Local frontend

```bash
cd frontend
npm install
npm run dev
```

## License

Proprietary — All rights reserved.
