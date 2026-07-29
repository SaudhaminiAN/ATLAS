# Spec 08 — Confluence

## Objective

Aggregate evidence from all analysis modules into a weighted confluence score and directional bias — the primary input to Trade Validation and Decision Engine.

## Scope

### In Scope

- Map each analysis module output to a normalized directional score
- Weighted scoring model (weights from active Strategy Profile — Spec 18)
- News Filter soft downgrade penalty (Spec 19)
- Confluence breakdown: per-module contribution
- Minimum evidence count before non-WAIT direction considered
- `ConfluenceService`
- Domain event: `confluence.calculated`
- REST: `GET /analysis/{symbol}/confluence`

### Out of Scope

- Final BUY/SELL/WAIT decision (Decision Engine — Spec 17)
- Hard validation rules (Validation module — Spec 09)

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| `MTFAnalysis` | Spec 04 | Yes |
| `TechnicalAnalysisResult` | Spec 05 | Yes |
| `SMCAnalysisResult` | Spec 06 | Yes |
| `PriceActionResult` | Spec 07 | Yes |
| `MarketContext` | Spec 03 | Yes |
| `NewsFilterStatus` | Spec 19 | Yes |
| `StrategyProfile` | Spec 18 | Yes |
| `trigger_bar` | Spec 02 (primary TF close) | Yes |

## Outputs

| Output | Type | Consumers |
|--------|------|-----------|
| `ConfluenceResult` | Domain model | Validation (09), Decision Engine (17), Journal (13) |
| `confluence.calculated` event | Domain event | Pipeline (20), Analytics (14) |

## Interfaces

```python
class ConfluenceServiceProtocol(Protocol):
    def calculate(
        self,
        instrument: Instrument,
        mtf: MTFAnalysis,
        technical: TechnicalAnalysisResult,
        smc: SMCAnalysisResult,
        price_action: PriceActionResult,
        context: MarketContext,
        news_status: NewsFilterStatus,
        strategy: StrategyProfile,
    ) -> ConfluenceResult: ...
```

## Database

| Table / Cache | Operation | Owner |
|---------------|-----------|-------|
| None (ephemeral) | — | — |
| `decisions.confluence_snapshot` | Persisted downstream | Spec 17 |

## Module → Directional Score Mapping

Each module produces `{ direction: Bias, score: Decimal }` where `score ∈ [0.0, 1.0]`.

A module counts toward `evidence_count` only if `score >= 0.30` for its direction.

### MTF (weight key: `mtf_alignment`)

```
direction = mtf.dominant_bias
if direction == NEUTRAL or not mtf.aligned:
    score = 0.0
else:
    score = mtf.alignment_score
```

### SMC (weight key: `smc_structure`)

```
direction = smc.directional_bias
if direction == NEUTRAL:
    score = 0.0
elif smc.last_bos and smc.last_bos.direction == direction:
    score = 1.0
elif smc.last_choch and smc.last_choch.direction == direction:
    score = 0.7
else:
    score = 0.5
```

### Price Action (weight key: `price_action`)

```
if price_action.strongest_pattern is None:
    direction = NEUTRAL; score = 0.0
else:
    p = price_action.strongest_pattern
    direction = p.direction
    score = p.strength
    if p.at_key_level: score = min(score × 1.1, 1.0)
```

### Technical Analysis (weight key: `technical_levels`)

```
if technical.bullish_context_score > technical.bearish_context_score:
    direction = BULLISH; score = technical.bullish_context_score
elif technical.bearish_context_score > technical.bullish_context_score:
    direction = BEARISH; score = technical.bearish_context_score
else:
    direction = NEUTRAL; score = 0.0
```

### Market Context (weight key: `market_context`)

```
direction = context.structural_bias
if direction == BULLISH:
    score = 0.8 if context.volatility_regime == NORMAL else 0.5
elif direction == BEARISH:
    score = 0.8 if context.volatility_regime == NORMAL else 0.5
else:
    score = 0.0
if context.volatility_regime == EXTREME:
    score = 0.0    # validation will block anyway
```

## Scoring Model

Weights loaded from active Strategy Profile (must sum to 1.0 ± 0.01):

```yaml
confluence:
  weights:
    mtf_alignment: 0.25
    smc_structure: 0.25
    price_action: 0.20
    technical_levels: 0.15
    market_context: 0.15
  min_score_for_direction: 0.70
  min_evidence_count: 3
```

### Score Calculation

```
For each module m with directional score (dir_m, score_m):
    if dir_m == BULLISH: bullish_raw += weight_m × score_m
    if dir_m == BEARISH: bearish_raw += weight_m × score_m

dominant_direction = argmax(bullish_raw, bearish_raw)
raw_score = max(bullish_raw, bearish_raw)

final_score = clamp(raw_score - news_status.confluence_penalty, 0.0, 1.0)

evidence_count = count of modules where score_m >= 0.30

if final_score < min_score_for_direction → suggested_direction = WAIT
if evidence_count < min_evidence_count → suggested_direction = WAIT
if has_directional_conflict → suggested_direction = WAIT
else → suggested_direction = dominant_direction (BUY or SELL)
```

### Directional Conflict

`has_directional_conflict = True` when ≥2 modules with weight ≥ 0.15 point in **opposite** directions with score ≥ 0.50 each.

Neutral modules do not participate in conflict detection.

## Domain Models

```python
@dataclass(frozen=True)
class ModuleScore:
    source: str
    direction: Bias
    score: Decimal
    weight: Decimal
    weighted_contribution: Decimal

@dataclass(frozen=True)
class EvidenceItem:
    source: str
    direction: Direction
    weight: Decimal
    score: Decimal
    weighted_contribution: Decimal
    description: str

@dataclass(frozen=True)
class ConfluenceResult:
    instrument: Instrument
    suggested_direction: Direction
    total_score: Decimal
    raw_score: Decimal
    bullish_raw: Decimal
    bearish_raw: Decimal
    news_penalty: Decimal
    module_scores: list[ModuleScore]
    evidence: list[EvidenceItem]
    evidence_count: int
    has_conflict: bool
    strategy_profile_id: str
    computed_at: datetime
```

## Edge Cases

| Case | Behavior |
|------|----------|
| Any required input module missing | Abort pipeline (critical failure) |
| Module returns NEUTRAL / score 0 | Contributes 0 to raw score; not counted in evidence |
| All modules neutral | `suggested_direction = WAIT`, score = 0 |
| News soft downgrade only | Subtract penalty; may drop below threshold → WAIT |
| Weights don't sum to 1.0 | Reject profile at load time (Spec 18) |
| Tie bullish_raw == bearish_raw | `suggested_direction = WAIT` |

## Acceptance Criteria

- [ ] Each module scored per mapping table (golden tests per module)
- [ ] Weights read from active Strategy Profile
- [ ] News soft downgrade penalty subtracted from score
- [ ] Score below threshold → `suggested_direction = WAIT`
- [ ] Fewer than `min_evidence_count` → WAIT
- [ ] Conflicting evidence → WAIT
- [ ] Full breakdown available via REST and event payload
- [ ] Unit tests: conflicting evidence, insufficient data, news penalty, all-neutral

## Dependencies

- Spec 03, 04, 05, 06, 07 (analysis modules)
- Spec 18 (Strategy Engine — weights)
- Spec 19 (News Filter — penalty)

## Downstream Consumers

- Trade Validation (Spec 09)
- Decision Engine (Spec 17)
