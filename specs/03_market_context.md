# Spec 03 — Market Context

## Objective

Classify the current trading environment for XAUUSD using **exact, reproducible rules**: session, volatility regime, spread conditions, and structural bias.

## Scope

### In Scope

- Session detection (UTC boundaries)
- Volatility regime from ATR percentile
- Spread assessment (stub in v1 mock)
- Structural bias from higher-TF swing structure
- `MarketContextService`
- Domain event: `market_context.updated`
- REST: `GET /analysis/{symbol}/context`

### Out of Scope

- News event blocking (News Filter — Spec 19)
- Correlation with other instruments
- Fundamental data

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| `OHLCVBar` (primary TF close) | Spec 02 event | Yes |
| Bar history (≥100 bars) | Spec 02 `ohlcv_bars` | Yes for ATR percentile |
| H4 bar history | Spec 02 | Yes for structural bias |
| `StrategyProfile.allowed_sessions` | Spec 18 | For session scoring |
| Spread data | Mock / future provider | No (stub in v1) |

## Outputs

| Output | Type | Consumers |
|--------|------|-----------|
| `MarketContext` | Domain model | Confluence (08), Validation (09) |
| `market_context.updated` | Domain event | Pipeline (20) |

## Interfaces

```python
class MarketContextServiceProtocol(Protocol):
    def compute(
        self,
        instrument: Instrument,
        primary_bars: list[OHLCVBar],
        bias_timeframe_bars: list[OHLCVBar],
        spread: Decimal | None = None,
    ) -> MarketContext: ...
```

## Database

| Table / Cache | Operation | Owner |
|---------------|-----------|-------|
| `context:{symbol}:latest` | Redis cache SET (TTL 60s) | This spec |
| Pipeline snapshot | JSONB in `pipeline_runs` | Spec 20 |

## Deterministic Rule Definitions

### Trading Sessions (UTC)

| Session | Start (inclusive) | End (exclusive) |
|---------|-------------------|-----------------|
| Asian | 00:00 | 08:00 |
| London | 08:00 | 16:00 |
| New York | 13:00 | 22:00 |
| London/NY Overlap | 13:00 | 16:00 |

`primary_session` = overlap if in overlap window; else prefer London > New York > Asian when multiple apply.

### Volatility Regime

ATR(14) on primary timeframe vs rolling 100-bar ATR distribution:

| Regime | Condition |
|--------|-----------|
| `low` | Current ATR ≤ 25th percentile |
| `normal` | 25th < ATR ≤ 75th percentile |
| `high` | 75th < ATR ≤ 95th percentile |
| `extreme` | ATR > **95th percentile** |

`extreme` triggers `volatility_check` validation failure (Spec 09).

### Structural Bias

On **H4** (configurable `context.bias_timeframe`):

| Bias | Condition |
|------|-----------|
| `bullish` | Last 2 swing highs = HH AND last 2 swing lows = HL |
| `bearish` | Last 2 swing highs = LH AND last 2 swing lows = LL |
| `neutral` | Mixed structure or insufficient swings |

Swing detection: 2-bar rule from Spec 06.

### Spread Assessment (v1 Stub)

| Status | Condition |
|--------|-----------|
| `normal` | Default in mock mode |
| `elevated` | Spread > 1.5× 20-bar average spread |

## Configuration

```yaml
market_context:
  bias_timeframe: H4
  atr_period: 14
  atr_percentile_lookback: 100
  min_bars_required: 100
```

## Domain Models

```python
@dataclass(frozen=True)
class MarketContext:
    instrument: Instrument
    primary_session: TradingSession
    active_sessions: list[TradingSession]
    volatility_regime: VolatilityRegime
    spread_status: SpreadStatus
    structural_bias: Bias
    atr_value: Decimal
    atr_percentile: Decimal
    computed_at: datetime
```

## Edge Cases

| Case | Behavior |
|------|----------|
| `< 100 bars` history | `volatility_regime = normal`, log warning |
| Insufficient H4 swings | `structural_bias = neutral` |
| Weekend / market closed | Use last available bar; session from bar timestamp |
| Spread data unavailable | `spread_status = normal` (mock) |

## Acceptance Criteria

- [ ] Session boundaries match UTC table (golden tests)
- [ ] Volatility regime uses 95th percentile for EXTREME
- [ ] Structural bias uses H4 swing rules
- [ ] Same bars → same context (deterministic)
- [ ] `market_context.updated` published with full snapshot
- [ ] REST returns latest context
- [ ] Unit tests: boundaries, volatility buckets, insufficient data

## Dependencies

- Spec 02 (Market Data)

## Downstream Consumers

- Confluence (Spec 08)
- Trade Validation (Spec 09)
- Decision Engine (Spec 17)
