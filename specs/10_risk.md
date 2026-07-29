# Spec 10 — Risk Management

## Objective

Calculate position size, SL, and TP using **exact formulas**. Enforce account limits.

## Scope

### In Scope

- Fixed fractional position sizing
- Structural SL/TP placement
- Account limit enforcement
- `RiskManagementService`
- Events: `risk.calculated`, `risk.limit.breached`
- REST: `GET/PUT /risk/profile`

### Out of Scope

- Trailing stops (Spec 12)
- Portfolio optimization

## Phase Note

**Phase 3.** Skipped when `pipeline.risk_enabled: false`.

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| `ValidationResult` (passed) | Spec 09 | Yes |
| `ConfluenceResult` | Spec 08 | Yes |
| `TechnicalAnalysisResult` | Spec 05 | Yes |
| `SMCAnalysisResult` | Spec 06 | Yes |
| `trigger_bar` | Spec 02 | Yes |
| `RiskProfile` | `risk_profiles` table | Yes |

## Outputs

| Output | Type | Consumers |
|--------|------|-----------|
| `RiskCheckResult` | Domain model | Decision Engine (17) |
| `RiskParameters` | Inside result | Execution (11) |
| `risk.calculated` / `risk.limit.breached` | Events | Decision Engine, alerts |

## Interfaces

```python
class RiskManagementServiceProtocol(Protocol):
    def calculate(
        self,
        direction: Direction,
        entry_price: Decimal,
        technical: TechnicalAnalysisResult,
        smc: SMCAnalysisResult,
        profile: RiskProfile,
        open_positions_count: int,
        daily_pnl: Decimal,
    ) -> RiskCheckResult: ...
```

## Database

| Table / Cache | Operation | Owner |
|---------------|-----------|-------|
| `risk_profiles` | SELECT, UPDATE | This spec |

## Stop-Loss Placement

**BUY:**
1. Candidate SL = below nearest bullish OB low OR nearest support (closer to entry, still below)
2. `sl = candidate - (0.2 × ATR)` buffer
3. Fail if SL distance < 5 pips

**SELL:** mirror above bearish OB high or resistance.

Fail if no level within `3 × ATR`.

## Take-Profit

```
risk_distance = abs(entry - stop_loss)
take_profit = entry ± (risk_distance × min_rr)    # + for BUY, - for SELL
```

Default `min_rr = 2.0`.

## Position Sizing

```
risk_amount = account_balance × (max_risk_percent / 100)
pip_risk = abs(entry - stop_loss) / pip_size
position_size = floor(risk_amount / (pip_risk × pip_value_per_lot), lot_step)
```

## Account Limits

| Limit | Block condition |
|-------|-----------------|
| Max risk per trade | `risk_amount` > balance × max_risk_percent |
| Max daily loss | Today's PnL ≤ -max_daily_loss |
| Max open positions | count ≥ max_open_positions |

## Configuration

```yaml
risk:
  max_risk_percent: 1.0
  max_daily_loss_percent: 3.0
  max_open_positions: 2
  min_rr: 2.0
  buffer_atr_multiplier: 0.2
  max_sl_distance_atr: 3.0
  min_sl_pips: 5
```

## Domain Models

```python
@dataclass(frozen=True)
class RiskParameters:
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    position_size: Decimal
    risk_amount: Decimal
    reward_risk_ratio: Decimal
    sl_basis: str

@dataclass(frozen=True)
class RiskCheckResult:
    within_limits: bool
    parameters: RiskParameters | None
    breach_reason: str | None
```

## Edge Cases

| Case | Behavior |
|------|----------|
| No structural SL within 3× ATR | `within_limits = False` |
| `position_size < min_lot` | Fail |
| Daily loss limit hit | `risk.limit.breached` |
| `risk_enabled: false` | Service not called |

## Acceptance Criteria

- [ ] SL/TP/sizing per formulas
- [ ] Limits enforced
- [ ] Skipped when `risk_enabled: false`
- [ ] Unit tests with fixture calculations

## Dependencies

- Spec 09, 05, 06, 18

## Downstream Consumers

- Decision Engine (17), Execution (11)
