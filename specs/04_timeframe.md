# Spec 04 — Multi-Timeframe Analysis

## Objective

Align directional bias across multiple timeframes using **exact rules** — producing MTF alignment score and conflict detection.

## Scope

### In Scope

- Per-timeframe bias from SMC trend or swing structure
- MTF alignment score and dominant bias
- Adjacent and distant conflict detection
- `MultiTimeframeAnalysisService`
- Domain event: `analysis.mtf.completed`

### Out of Scope

- Full SMC/PA analysis (separate specs)
- Automatic timeframe selection

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Closed bars per TF | Spec 02 | Yes |
| `SMCAnalysisResult` per TF | Spec 06 | Optional (fallback to swing) |
| `TechnicalAnalysisResult` per TF | Spec 05 | For `key_levels` |
| `StrategyProfile.active_timeframes` | Spec 18 | Yes |
| `trigger_bar` | Spec 02 primary TF | Yes |

## Outputs

| Output | Type | Consumers |
|--------|------|-----------|
| `MTFAnalysis` | Domain model | Confluence (08), Validation (09) |
| `analysis.mtf.completed` | Domain event | Pipeline (20) |

## Interfaces

```python
class MultiTimeframeAnalysisServiceProtocol(Protocol):
    def analyze(
        self,
        instrument: Instrument,
        timeframe_bars: dict[Timeframe, list[OHLCVBar]],
        smc_results: dict[Timeframe, SMCAnalysisResult | None],
        technical_results: dict[Timeframe, TechnicalAnalysisResult],
        strategy: StrategyProfile,
    ) -> MTFAnalysis: ...
```

## Database

| Table / Cache | Operation | Owner |
|---------------|-----------|-------|
| None (ephemeral) | — | — |
| Pipeline snapshot | JSONB in `pipeline_runs` | Spec 20 |

## Configuration

```yaml
mtf:
  timeframes: [D1, H4, H1, M15]
  primary: M15
  alignment_threshold: 0.75
  bias_source: smc_trend
```

## Per-Timeframe Bias Rules

Using last **closed** bar only per TF.

### Method A: SMC Trend (default)

| Bias | Condition |
|------|-----------|
| `bullish` | SMC trend = uptrend AND no bearish CHoCH in last 10 bars |
| `bearish` | SMC trend = downtrend AND no bullish CHoCH in last 10 bars |
| `neutral` | Otherwise |

### Method B: Swing Structure (fallback)

| Bias | Condition |
|------|-----------|
| `bullish` | HH + HL |
| `bearish` | LH + LL |
| `neutral` | Otherwise |

### Per-TF Confidence

```
1.0  if bias set and last BOS agrees
0.6  if bias set but no recent BOS
0.3  if neutral
```

### `key_levels` on TimeframeBias

Top 3 levels from `TechnicalAnalysisResult.key_levels` for that TF (strength ≥ 0.5).

## Alignment Score

```
bullish_count / bearish_count / total → alignment_score, dominant_bias
Tie → alignment_score = 0.0, dominant_bias = neutral
aligned = alignment_score >= threshold (default 0.75)
```

## Conflict Detection

- `has_conflict`: adjacent TF pairs (D1↔H4, H4↔H1, H1↔M15) disagree (bullish vs bearish)
- `distant_conflict`: D1 vs M15 disagree without adjacent conflict (warning only)
- Neutral does not conflict

## Domain Models

```python
@dataclass(frozen=True)
class TimeframeBias:
    timeframe: Timeframe
    bias: Bias
    confidence: Decimal
    trend_source: str
    key_levels: list[PriceLevel]

@dataclass(frozen=True)
class MTFAnalysis:
    instrument: Instrument
    biases: list[TimeframeBias]
    alignment_score: Decimal
    dominant_bias: Bias
    has_conflict: bool
    distant_conflict: bool
    aligned: bool
    computed_at: datetime
```

## Edge Cases

| Case | Behavior |
|------|----------|
| SMC unavailable for TF | Fall back to swing structure |
| Single TF in profile | alignment_score = 1.0 if non-neutral else 0.0 |
| All TFs neutral | `dominant_bias = neutral`, `aligned = False` |
| Insufficient bars for TF | TF bias = neutral, log warning |

## Acceptance Criteria

- [ ] Each TF uses last closed bar only (no look-ahead test)
- [ ] Bias rules match SMC or swing definitions
- [ ] `key_levels` sourced from Spec 05
- [ ] Alignment and conflict per formulas
- [ ] Event published with full snapshot
- [ ] Unit tests: aligned, conflict, neutral, single-TF

## Dependencies

- Spec 02, 03, 05, 06, 18

## Downstream Consumers

- Confluence (Spec 08)
- Trade Validation (Spec 09)
