# ATLAS Database Design

## Overview

PostgreSQL is the primary datastore. Redis handles caching and ephemeral state. Schema follows domain boundaries with clear audit trails.

## Design Principles

- Every trade and decision is immutable once recorded (append-only audit where needed)
- Soft deletes only for user-facing entities; hard deletes for GDPR compliance workflows
- UUIDs as primary keys for distributed-friendly IDs
- Timestamps in UTC (`timestamptz`)
- Foreign keys enforced at database level

## Core Tables (Planned)

### users

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| email | VARCHAR UNIQUE | |
| password_hash | VARCHAR | |
| is_active | BOOLEAN | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### instruments

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| symbol | VARCHAR UNIQUE | e.g. `XAUUSD` |
| display_name | VARCHAR | |
| pip_size | DECIMAL | |
| lot_size | DECIMAL | |
| is_active | BOOLEAN | |

### ohlcv_bars

| Column | Type | Notes |
|--------|------|-------|
| id | BIGSERIAL PK | |
| instrument_id | UUID FK | |
| timeframe | VARCHAR | e.g. `M15`, `H1` |
| open_time | TIMESTAMPTZ | Bar open |
| open | DECIMAL | |
| high | DECIMAL | |
| low | DECIMAL | |
| close | DECIMAL | |
| volume | DECIMAL | |
| is_outlier | BOOLEAN | Excluded from analysis if true |
| quality_flags | JSONB | Validation flags |

**Index:** `(instrument_id, timeframe, open_time DESC)` UNIQUE

### strategy_profiles

| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR PK | e.g. `xauusd_conservative` |
| name | VARCHAR | Display name |
| config | JSONB | Weights, thresholds, rule toggles |
| is_active | BOOLEAN | Only one active at a time |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### economic_events

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| name | VARCHAR | e.g. `US CPI` |
| currency | VARCHAR | |
| impact | VARCHAR | `high`, `medium`, `low` |
| scheduled_at | TIMESTAMPTZ | UTC |
| actual | DECIMAL NULL | |
| forecast | DECIMAL NULL | |
| previous | DECIMAL NULL | |
| source | VARCHAR | Provider name |

**Index:** `(scheduled_at, impact)`

### pipeline_runs

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| correlation_id | VARCHAR | End-to-end trace ID |
| instrument_id | UUID FK | |
| trigger_timeframe | VARCHAR | |
| trigger_bar_time | TIMESTAMPTZ | |
| status | VARCHAR | `completed`, `failed` |
| stage_results | JSONB | Per-stage timing and status |
| duration_ms | INT | |
| created_at | TIMESTAMPTZ | |

### decisions

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| instrument_id | UUID FK | |
| correlation_id | VARCHAR | Pipeline trace ID |
| direction | VARCHAR | `BUY`, `SELL`, `WAIT` |
| is_actionable | BOOLEAN | True only for validated BUY/SELL |
| reason | VARCHAR | Primary reason (especially for WAIT) |
| confidence | DECIMAL | 0.0–1.0 confluence score |
| strategy_profile_id | VARCHAR FK | |
| confluence_snapshot | JSONB | Full evidence breakdown |
| validation_result | JSONB | Pass/fail per rule |
| risk_snapshot | JSONB | SL, TP, size (null for WAIT) |
| news_status | JSONB | News filter state at decision time |
| created_at | TIMESTAMPTZ | |

### trades

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| decision_id | UUID FK | Link to originating decision |
| instrument_id | UUID FK | |
| direction | VARCHAR | |
| entry_price | DECIMAL | |
| stop_loss | DECIMAL | |
| take_profit | DECIMAL | |
| position_size | DECIMAL | Lots or units |
| status | VARCHAR | `pending`, `open`, `closed`, `cancelled` |
| opened_at | TIMESTAMPTZ | |
| closed_at | TIMESTAMPTZ | |
| pnl | DECIMAL | Realized P&L |
| created_at | TIMESTAMPTZ | |

### trade_events

Append-only lifecycle log for each trade.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| trade_id | UUID FK | |
| event_type | VARCHAR | `opened`, `sl_moved`, `partial_close`, etc. |
| payload | JSONB | Event-specific data |
| created_at | TIMESTAMPTZ | |

### decision_explanations

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| decision_id | UUID FK UNIQUE | One explanation per decision |
| summary | TEXT | |
| evidence_narrative | TEXT | |
| risk_narrative | TEXT NULL | |
| wait_reason_detail | TEXT NULL | |
| model_version | VARCHAR | |
| created_at | TIMESTAMPTZ | |

### journal_entries

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| trade_id | UUID FK NULL | Optional link |
| user_id | UUID FK | |
| content | TEXT | Trader notes |
| tags | VARCHAR[] | |
| created_at | TIMESTAMPTZ | |

### risk_profiles

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK | |
| max_risk_percent | DECIMAL | Per trade |
| max_daily_loss | DECIMAL | |
| max_open_positions | INT | |
| settings | JSONB | Extended config |
| updated_at | TIMESTAMPTZ | |

## Redis Keys (Ephemeral)

| Key Pattern | Purpose | TTL |
|-------------|---------|-----|
| `session:{user_id}` | Active session | Configurable |
| `bars:{symbol}:{tf}:latest` | Latest bar cache | 60s |
| `decision:{symbol}:latest` | Latest decision cache | 30s |
| `strategy:active` | Active strategy profile | 300s |
| `news:events:upcoming` | Cached economic calendar | 900s |
| `pipeline:dedupe:{symbol}:{tf}:{time}` | Pipeline dedupe | 60s |
| `ratelimit:{user_id}:{endpoint}` | Rate limiting | 60s |

## Migrations

- Managed by Alembic under `backend/alembic/`
- One migration per logical schema change
- Never edit applied migrations; create new ones

## Backup & Retention

- Daily PostgreSQL backups in production
- OHLCV retention policy configurable (default: 2 years)
- Decision and trade records retained indefinitely for audit
