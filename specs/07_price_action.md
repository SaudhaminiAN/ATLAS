# Spec 07 — Price Action

## Objective

Detect candlestick patterns using **exact numeric rules**; score higher at key levels.

## Scope

### In Scope

- Pin bar, engulfing, inside bar, displacement
- Key level proximity scoring
- `PriceActionService`
- Domain event: `analysis.price_action.completed`

### Out of Scope

- Harmonic patterns, Elliott Wave
- Standalone signals

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| `OHLCVBar` history (≥3 bars) | Spec 02 | Yes |
| `TechnicalAnalysisResult.key_levels` | Spec 05 | Yes |
| `SMCAnalysisResult` (OB, liquidity, FVG) | Spec 06 | Yes |
| `timeframe`, `instrument` | Pipeline | Yes |

## Outputs

| Output | Type | Consumers |
|--------|------|-----------|
| `PriceActionResult` | Domain model | Confluence (08) |
| `analysis.price_action.completed` | Domain event | Pipeline (20) |

## Interfaces

```python
class PriceActionServiceProtocol(Protocol):
    def analyze(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        bars: list[OHLCVBar],
        key_levels: list[PriceLevel],
        smc: SMCAnalysisResult,
    ) -> PriceActionResult: ...
```

## Database

| Table / Cache | Operation | Owner |
|---------------|-----------|-------|
| None (ephemeral) | — | — |

## Deterministic Pattern Rules

Evaluated on **most recently closed bar** (index -1).

### Pin Bar

```
range = high - low
if range == 0: skip (doji)

Bullish pin: lower_wick >= 0.66 × range AND body <= 0.33 × range
Bearish pin: upper_wick >= 0.66 × range AND body <= 0.33 × range
```

### Engulfing, Inside Bar, Displacement

Per existing formulas (see prior spec). Displacement: body ≥ 1.5× ATR.

### Key Level Proximity

| Condition | Multiplier |
|-----------|------------|
| At S/R | × 1.5 |
| At order block | × 1.5 |
| At liquidity pool | × 1.3 |
| At FVG | × 1.2 |
| No level nearby | × 0.6 |

`level_proximity_pct` default: 0.15%. Final strength capped at 1.0.

Patterns below `min_pattern_strength` (0.3) excluded.

## Domain Models

```python
@dataclass(frozen=True)
class PriceActionResult:
    instrument: Instrument
    timeframe: Timeframe
    patterns: list[CandlePattern]
    strongest_pattern: CandlePattern | None
    computed_at: datetime
```

## Edge Cases

| Case | Behavior |
|------|----------|
| `range = 0` (doji) | Skip pin bar; other patterns may still apply |
| Multiple patterns same bar | All detected; `strongest_pattern` = highest strength |
| No patterns | `strongest_pattern = None`, score 0 in Confluence |
| `< 3 bars` | Return empty result; log warning |

## Acceptance Criteria

- [ ] Golden tests per pattern (pass and near-miss)
- [ ] Doji/range=0 handled
- [ ] Key level proximity correct
- [ ] Multiple patterns ranked correctly
- [ ] Deterministic output

## Dependencies

- Spec 02, 05, 06

## Downstream Consumers

- Confluence (Spec 08)
