# Spec 09 — Trade Validation

## Objective

Apply deterministic pass/fail rules to confluence output. No trade proceeds unless every **enabled** rule passes.

## Scope

### In Scope

- Rule engine with declarative rule definitions
- Rules toggled per Strategy Profile (Spec 18)
- Built-in rules (all defined below)
- `TradeValidationService`
- Domain event: `validation.completed`
- Output: `ValidationResult` with per-rule pass/fail and reasons

### Out of Scope

- Position sizing (Risk module — Spec 10)
- AI override of any rule

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| `ConfluenceResult` | Spec 08 | Yes |
| `MTFAnalysis` | Spec 04 | Yes |
| `MarketContext` | Spec 03 | Yes |
| `TechnicalAnalysisResult` | Spec 05 | For R:R rule |
| `SMCAnalysisResult` | Spec 06 | For R:R rule |
| `NewsFilterStatus` | Spec 19 | Yes |
| `StrategyProfile` | Spec 18 | Yes |
| `trigger_bar` | Spec 02 | Yes (entry price = close) |

## Outputs

| Output | Type | Consumers |
|--------|------|-----------|
| `ValidationResult` | Domain model | Decision Engine (17), Risk (10), Journal (13) |
| `validation.completed` event | Domain event | Pipeline (20) |

## Interfaces

```python
class ValidationRuleProtocol(Protocol):
    name: str
    def evaluate(self, context: ValidationContext) -> ValidationRuleResult: ...

class TradeValidationServiceProtocol(Protocol):
    def validate(self, context: ValidationContext) -> ValidationResult: ...
```

## Database

| Table / Cache | Operation | Owner |
|---------------|-----------|-------|
| `decisions.validation_result` | JSONB snapshot | Spec 17 |

## Rule Definitions

| Rule | Pass Condition | Default |
|------|----------------|---------|
| `mtf_alignment_minimum` | `MTFAnalysis.aligned == True` (score ≥ 0.75) | Enabled |
| `confluence_score_minimum` | `ConfluenceResult.total_score ≥ profile.min` (default 0.70) | Enabled |
| `no_counter_trend` | Direction not against D1 **and** H4 bias | Enabled |
| `minimum_rr_potential` | Structural R:R ≥ 2.0 (see algorithm) | Enabled |
| `news_block` | `NewsFilterStatus.is_blocked == False` | Enabled |
| `session_check` | `MarketContext.primary_session ∈ profile.allowed_sessions` | Enabled |
| `spread_check` | `MarketContext.spread_status != ELEVATED` (stub: pass in mock) | Enabled |
| `volatility_check` | `MarketContext.volatility_regime != EXTREME` | Enabled |

Each rule returns `{ rule_name, passed, reason, enabled }`.

Disabled rules (via Strategy Profile) are **skipped**, not failed.

### `minimum_rr_potential` Algorithm

Uses primary timeframe close as entry. Direction from `ConfluenceResult.suggested_direction`.

**BUY:**

```
entry = trigger_bar.close
stop_loss = technical.nearest_support
  OR nearest unmitigated bullish OB low (Spec 06)
  OR None

take_profit = technical.nearest_resistance OR None

if stop_loss is None or take_profit is None:
    FAIL — "No structural SL/TP levels"

risk = entry - stop_loss
reward = take_profit - entry

if risk <= 0:
    FAIL — "Invalid risk distance"

rr = reward / risk
PASS if rr >= 2.0 else FAIL — "R:R {rr:.2f} below minimum 2.0"
```

**SELL:** mirror (SL above entry at resistance/OB high, TP at support).

### `no_counter_trend` Algorithm

```
d1_bias = MTFAnalysis.biases[D1].bias
h4_bias = MTFAnalysis.biases[H4].bias
direction = ConfluenceResult.suggested_direction

if direction == BUY and (d1_bias == BEARISH or h4_bias == BEARISH):
    FAIL
if direction == SELL and (d1_bias == BULLISH or h4_bias == BULLISH):
    FAIL
else PASS
```

Neutral D1/H4 bias does not block.

### `volatility_check`

Uses `MarketContext.volatility_regime` from Spec 03. **EXTREME** = ATR > 95th percentile (aligned with Spec 03).

## Domain Models

```python
@dataclass(frozen=True)
class ValidationContext:
    confluence: ConfluenceResult
    mtf: MTFAnalysis
    context: MarketContext
    technical: TechnicalAnalysisResult
    smc: SMCAnalysisResult
    news: NewsFilterStatus
    strategy: StrategyProfile
    trigger_bar: OHLCVBar

@dataclass(frozen=True)
class ValidationRuleResult:
    rule_name: str
    passed: bool
    reason: str
    enabled: bool

@dataclass(frozen=True)
class ValidationResult:
    instrument: Instrument
    direction: Direction
    is_valid: bool
    rules: list[ValidationRuleResult]
    failed_rules: list[str]
    strategy_profile_id: str
    validated_at: datetime
```

## Edge Cases

| Case | Behavior |
|------|----------|
| `suggested_direction == WAIT` | Skip validation; `is_valid = False`, reason = "No direction to validate" |
| All rules disabled | `is_valid = True` (dangerous — profile validation rejects this at load) |
| Missing nearest level for R:R | Rule fails with explicit reason |
| Session = overlap | Pass if `overlap` ∈ `allowed_sessions` |
| Mock spread mode | `spread_check` always passes |

## Acceptance Criteria

- [ ] All 8 rules implemented per definition
- [ ] Disabled rules skipped, not failed
- [ ] `is_valid = False` if any enabled rule fails
- [ ] `minimum_rr_potential` golden tests with fixture levels
- [ ] `session_check` integrates with Strategy Profile
- [ ] `volatility_check` uses Spec 03 EXTREME definition (95th percentile)
- [ ] Unit test per rule: pass, fail, disabled
- [ ] Integration test: confluence → validation → decision

## Dependencies

- Spec 08 (Confluence)
- Spec 03, 04, 05, 06 (context for rules)
- Spec 18 (Strategy Engine — rule toggles)
- Spec 19 (News Filter)

## Downstream Consumers

- Decision Engine (Spec 17)
- Risk Management (Spec 10)
