# Spec 18 — Strategy Engine

## Objective

Manage configurable strategy profiles that tune weights, thresholds, and rules without code changes.

## Scope

### In Scope

- `StrategyProfile` configuration bundle
- Load, validate, serve active profile
- Default: `xauusd_conservative`
- Domain event: `strategy.profile.changed`
- REST: `GET /strategy/profiles`, `GET /strategy/active`, `PUT /strategy/active`

### Out of Scope

- ML optimization
- Multi-instrument profiles (v1)
- Auto profile switching

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Profile ID (switch) | REST `PUT /strategy/active` | On change |
| `strategy_profiles` DB rows | PostgreSQL | Yes |
| Seed config | Migration / fixture | At startup |

## Outputs

| Output | Type | Consumers |
|--------|------|-----------|
| `StrategyProfile` (active) | Domain model | All analysis modules |
| `strategy.profile.changed` | Domain event | Confluence, Validation, Pipeline |

## Interfaces

```python
class StrategyEngineServiceProtocol(Protocol):
    def get_active(self) -> StrategyProfile: ...
    def set_active(self, profile_id: str) -> StrategyProfile: ...
    def list_profiles(self) -> list[StrategyProfile]: ...
    def validate_profile(self, config: dict) -> list[str]: ...  # errors
```

## Database

| Table / Cache | Operation | Owner |
|---------------|-----------|-------|
| `strategy_profiles` | SELECT, UPDATE `is_active` | This spec |
| `strategy:active` | Redis cache (TTL 300s) | This spec |

## Default Profile

```yaml
strategy:
  id: xauusd_conservative
  name: XAUUSD Conservative
  min_confluence_score: 0.70
  enabled_directions: [BUY, SELL]
  confluence_weights:
    mtf_alignment: 0.25
    smc_structure: 0.25
    price_action: 0.20
    technical_levels: 0.15
    market_context: 0.15
  active_timeframes: [D1, H4, H1, M15]
  allowed_sessions: [london, new_york, overlap]
  validation_rules:
    mtf_alignment_minimum: true
    confluence_score_minimum: true
    no_counter_trend: true
    minimum_rr_potential: true
    news_block: true
    session_check: true
    spread_check: true
    volatility_check: true
```

## Profile Validation Schema

Rejected at load if:

| Rule | Constraint |
|------|------------|
| Weights sum | Must equal 1.0 ± 0.01 |
| `min_confluence_score` | 0.0–1.0 |
| `enabled_directions` | Non-empty |
| `active_timeframes` | ≥ 2, valid TF enums |
| `allowed_sessions` | Non-empty |
| All validation rules disabled | Reject — at least 1 must be enabled |
| Unknown rule name | Reject |

## Domain Models

```python
@dataclass(frozen=True)
class StrategyProfile:
    id: str
    name: str
    min_confluence_score: Decimal
    enabled_directions: list[Direction]
    confluence_weights: dict[str, Decimal]
    active_timeframes: list[Timeframe]
    allowed_sessions: list[TradingSession]
    validation_rule_flags: dict[str, bool]
    is_active: bool
    updated_at: datetime
```

## Edge Cases

| Case | Behavior |
|------|----------|
| Invalid profile on switch | Reject with 400 + error list |
| No active profile at startup | Load default seed |
| Profile changed mid-pipeline | Next pipeline run uses new profile |
| Concurrent switch requests | Last write wins; emit single event |

## Acceptance Criteria

- [ ] Active profile at startup and on change
- [ ] Confluence reads weights; Validation reads rule toggles
- [ ] `session_check` rule flag honored (Spec 09)
- [ ] Invalid config rejected with clear errors
- [ ] Profile change without restart
- [ ] Unit tests: validation schema, direction filter

## Dependencies

- Spec 01 (Project Setup)

## Downstream Consumers

- Confluence (08), Validation (09), Decision Engine (17), Pipeline (20), MTF (04)
