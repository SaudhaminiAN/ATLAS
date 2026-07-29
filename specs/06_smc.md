# Spec 06 — Smart Money Concepts (SMC)

## Objective

Detect institutional-style market structure using **exact, reproducible rules**.

## Scope

### In Scope

- Swing points, BOS, CHoCH
- Liquidity pools, order blocks, FVGs
- `SmartMoneyConceptsService`
- Domain event: `analysis.smc.completed`

### Out of Scope

- Automated entry at order blocks
- Multi-instrument analysis
- Subjective SMC interpretations

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| `OHLCVBar` history | Spec 02 | Yes (min 50 bars) |
| `timeframe`, `instrument` | Pipeline | Yes |
| `SwingDetector` | Spec 05 shared util | Yes |

## Outputs

| Output | Type | Consumers |
|--------|------|-----------|
| `SMCAnalysisResult` | Domain model | Confluence (08), PA (07), MTF (04), Risk (10) |
| `analysis.smc.completed` | Domain event | Pipeline (20) |

## Interfaces

```python
class SmartMoneyConceptsServiceProtocol(Protocol):
    def analyze(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        bars: list[OHLCVBar],
    ) -> SMCAnalysisResult: ...
```

## Database

| Table / Cache | Operation | Owner |
|---------------|-----------|-------|
| None (ephemeral) | — | — |

## Deterministic Rule Definitions

### Swing Points

A **swing high** at bar `i` requires bars `i±2` to exist:
- `high[i] > high[i-1]` AND `high[i] > high[i-2]`
- `high[i] > high[i+1]` AND `high[i] > high[i+2]`

A **swing low** at bar `i`: mirror with `low`. **No swing on last 2 bars** (lookahead confirmation).

### Break of Structure (BOS)

- **Bullish BOS:** Close breaks above most recent swing high in downtrend
- **Bearish BOS:** Close breaks below most recent swing low in uptrend
- Confirmed on **close**, not wick

### Change of Character (CHoCH)

- **Bullish CHoCH:** In downtrend, close breaks above most recent lower high
- **Bearish CHoCH:** In uptrend, close breaks below most recent higher low

Trend: last 2 swing highs/lows (HH/HL = uptrend, LH/LL = downtrend).

### Order Blocks

1. Displacement candle: body ≥ `1.5 × ATR`
2. OB = last opposing-color candle before displacement
3. Zone = `[min(open, close), max(open, close)]`
4. **Mitigated** when price trades through 50% midpoint

### Liquidity Pools

Equal highs/lows within 0.1% tolerance. Strength: 2 touches = 0.5, 3 = 0.75, 4+ = 1.0.

### Fair Value Gaps (FVG)

Bullish: candle1.high < candle3.low. Bearish: inverse. Filled at 50%+ gap penetration.

## Configuration

```yaml
smc:
  swing_lookback: 2
  displacement_atr_multiplier: 1.5
  ob_mitigation_pct: 0.50
  equal_level_tolerance_pct: 0.001
  fvg_fill_pct: 0.50
  min_bars: 50
```

## Domain Models

```python
@dataclass(frozen=True)
class SMCAnalysisResult:
    instrument: Instrument
    timeframe: Timeframe
    trend: Trend
    last_bos: StructureBreak | None
    last_choch: StructureBreak | None
    order_blocks: list[OrderBlock]
    liquidity_pools: list[LiquidityPool]
    fair_value_gaps: list[FairValueGap]
    directional_bias: Bias
    computed_at: datetime
```

## Edge Cases

| Case | Behavior |
|------|----------|
| `< 50 bars` | Return neutral result; log warning |
| Last 2 bars | No new swing points (lookahead required) |
| Doji displacement | Body = 0 → not displacement |
| Multiple OBs | Return unmitigated only, max 5 |

## Acceptance Criteria

- [ ] Golden tests per rule (swing, BOS, OB, FVG)
- [ ] No look-ahead on live last bar
- [ ] Same input → same output
- [ ] No BUY/SELL signal emitted
- [ ] Shared swing utility with Spec 05

## Dependencies

- Spec 02, 05 (swing utility)

## Downstream Consumers

- Confluence (08), Price Action (07), MTF (04), Validation (09), Risk (10)
