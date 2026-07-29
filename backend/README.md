# ATLAS Backend

Python 3.11+ / FastAPI modular monolith.

## Local development

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[dev]"
cp ../.env.example ../.env
uvicorn atlas.presentation.api.main:app --reload --app-dir src
```

## Tests

```bash
pytest
```

## Migrations

```bash
alembic upgrade head
```
