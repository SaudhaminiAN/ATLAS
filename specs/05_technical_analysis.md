# Spec 05 — Technical Analysis

## Objective

Provide structural technical context using **exact numeric rules**. Evidence only; never standalone signals.

## Scope

### In Scope

- Swing high/low detection (shared utility with Spec 06)
- S/R levels with strength scoring
- Trend classification
- Indicator context (EMA, RSI, ATR)
- Directional context scores for Confluence
- `TechnicalAnalysisService`
- Domain event: `analysis.technical.completed`

### Out of Scope

- Signal generation from indicator crossovers
- Chart patterns (Spec 07)
- SMC concepts (Spec 06)

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| `OHLCVBar` history | Spec 02 | Yes (min 200 bars for EMA200) |
| `timeframe` | Pipeline config | Yes |
| `instrument` | Pipeline | Yes |

## Outputs

| Output | Type | Consumers |
|--------|------|-----------|
| `TechnicalAnalysisResult` | Domain model | Confluence (08), PA (07), Validation (09) |
| `analysis.technical.completed` | Domain event | Pipeline (20) |

## Interfaces

```python
class TechnicalAnalysisServiceProtocol(Protocol):
    def analyze(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        bars: list[OHLCVBar],
    ) -> TechnicalAnalysisResult: ...

class SwingDetectorProtocol(Protocol):
    """Shared utility used by Specs 05, 06, 03."""
    def detect_swings(self, bars: list[OHLCVBar], lookback: int) -> list[SwingPoint]: ...
```

## Database

| Table / Cache | Operation | Owner |
|---------------|-----------|-------|
| None (ephemeral) | — | — |

## Deterministic Rule Definitions

### Swing Points

2-bar lookback and 2-bar lookahead (configurable, default 2). Same as Spec 06.

### Support & Resistance

Levels from swing points; merge within `merge_tolerance_pct` (0.1%).

| Touches | Strength |
|---------|----------|
| 1 | 0.3 |
| 2 | 0.5 |
| 3 | 0.75 |
| 4+ | 1.0 |

Return top 5 (max 3 support, max 3 resistance).

### Trend

| Trend | Condition |
|-------|-----------|
| `uptrend` | HH + HL |
| `downtrend` | LH + LL |
| `ranging` | Otherwise |

### Indicator Context

| Indicator | Output |
|-----------|--------|
| EMA 20/50/200 | `price_vs_ema20`: ±1/0 |
| RSI 14 | 0–100; zones <30, >70 |
| ATR 14 | Raw value |

**Context scores** (max 0.5 each direction):

```
bullish: +0.3 uptrend, +0.2 close>ema20>ema50, +0.1 40≤rsi≤60
bearish: mirror
```

### Nearest Levels

```
nearest_support = max(support where price < close) or None
nearest_resistance = min(resistance where price > close) or None
```

## Configuration

```yaml
technical_analysis:
  swing_lookback: 2
  merge_tolerance_pct: 0.001
  ema_periods: [20, 50, 200]
  min_bars: 200
```

## Domain Models

```python
@dataclass(frozen=True)
class TechnicalAnalysisResult:
    instrument: Instrument
    timeframe: Timeframe
    trend: Trend
    key_levels: list[PriceLevel]
    nearest_support: Decimal | None
    nearest_resistance: Decimal | None
    indicator_context: dict[str, Decimal]
    bullish_context_score: Decimal
    bearish_context_score: Decimal
    computed_at: datetime
```

## Edge Cases

| Case | Behavior |
|------|----------|
| `< 200 bars` | EMA200 omitted; log warning; use available EMAs |
| No S/R levels | `nearest_support/resistance = None` |
| `range = 0` bar | Skip in swing detection |
| Insufficient swings | `trend = ranging` |

## Acceptance Criteria

- [ ] Swing points match Spec 06 (shared utility test)
- [ ] S/R merged and strength-scored
- [ ] Context scores capped at 0.5
- [ ] No trade direction returned
- [ ] Golden tests with known sequences
- [ ] `nearest_*` null handling tested

## Dependencies

- Spec 02 (Market Data)

## Downstream Consumers

- Confluence (08), Price Action (07), Validation (09), MTF (04)
