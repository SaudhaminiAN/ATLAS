# Spec 12 — Position Management

## Objective

Manage open positions after entry using **exact rules**: breakeven moves, trailing stops, partial exits, and close detection.

## Scope

### In Scope

- Monitor open positions on each primary-TF bar close
- Breakeven SL move at configured R level
- ATR-based or structure-based trailing stop
- Partial exit at TP1, remainder at TP2
- Close detection: SL hit, TP hit, manual close
- `PositionManagementService`
- Domain events: `trade.sl_moved`, `trade.partial_closed`, `trade.closed`
- WebSocket: position update channel

### Out of Scope

- Scaling into positions
- Hedging
- Live broker order modification (paper mode updates virtual SL/TP)

## Phase Note

**Phase 3 module.** Requires Execution Engine (Spec 11) and open trades. Not active during Analysis MVP.

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Open `Trade` record | Spec 11 (`trades` table) | Yes |
| `OHLCVBar` (primary TF) | Spec 02 `market_data.bar.received` | Yes |
| `RiskParameters` | Trade record (entry, SL, TP, size) | Yes |
| `PositionManagementConfig` | Strategy Profile / env | Yes |
| `ATR` (14) | Computed from bars | For trailing |

## Outputs

| Output | Type | Consumers |
|--------|------|-----------|
| Updated `Trade` | DB record | Journal (13), Analytics (14) |
| `trade.sl_moved` | Domain event | Journal, WebSocket |
| `trade.partial_closed` | Domain event | Journal, Analytics |
| `trade.closed` | Domain event | Journal, Analytics (14) |
| `trade_events` row | Append-only audit | Journal (13) |

## Interfaces

```python
class PositionManagementServiceProtocol(Protocol):
    async def on_bar(self, bar: OHLCVBar) -> list[PositionAction]: ...

    async def close_position_manual(
        self, trade_id: UUID, reason: str
    ) -> Trade: ...
```

## Database

| Table / Cache | Operation | Owner |
|---------------|-----------|-------|
| `trades` | UPDATE status, SL, TP, size, pnl | This spec |
| `trade_events` | INSERT append-only | This spec |

## Domain Models

```python
@dataclass(frozen=True)
class OpenPosition:
    trade_id: UUID
    instrument: Instrument
    direction: Direction
    entry_price: Decimal
    current_sl: Decimal
    current_tp: Decimal
    position_size: Decimal
    remaining_size: Decimal
    risk_distance: Decimal          # abs(entry - initial_sl)
    status: PositionStatus          # open, partial, closed

@dataclass(frozen=True)
class PositionAction:
    trade_id: UUID
    action_type: ActionType         # breakeven, trail_sl, partial_close, close
    old_sl: Decimal | None
    new_sl: Decimal | None
    closed_size: Decimal | None
    close_price: Decimal | None
    reason: str
    bar_time: datetime

@dataclass(frozen=True)
class PositionManagementConfig:
    breakeven_at_r: Decimal
    trailing_enabled: bool
    trailing_method: str            # "atr" | "structure"
    trailing_atr_multiplier: Decimal
    partial_exit_enabled: bool
    partial_exit_percent: Decimal
    partial_exit_at_r: Decimal
    tp2_at_r: Decimal
```

## Management Rules

### Breakeven

Triggered when unrealized profit ≥ `breakeven_at_r × risk_distance` (default 1.0R):

```
BUY:  if bar.high >= entry + (breakeven_at_r × risk_distance)
      → move SL to entry (no buffer in v1)
SELL: if bar.low <= entry - (breakeven_at_r × risk_distance)
      → move SL to entry
```

Only fires once per trade. Logged as `trade.sl_moved` with `reason = "breakeven"`.

### Trailing Stop (ATR method)

After breakeven triggered:

```
BUY:  new_sl = bar.close - (trailing_atr_multiplier × ATR)
      update only if new_sl > current_sl
SELL: new_sl = bar.close + (trailing_atr_multiplier × ATR)
      update only if new_sl < current_sl
```

Default `trailing_atr_multiplier = 1.5`.

### Trailing Stop (structure method)

```
BUY:  new_sl = latest swing low since entry (Spec 06 swing rules)
SELL: new_sl = latest swing high since entry
      update only if improves current_sl
```

### Partial Exit

When profit ≥ `partial_exit_at_r × risk_distance` (default 1.5R) and not yet taken:

```
close_size = position_size × (partial_exit_percent / 100)   # default 50%
remaining_size = position_size - close_size
realized_pnl_partial = close_size × (close_price - entry)   # BUY; inverse SELL
```

Log `trade.partial_closed`. Move TP to `tp2_at_r` (default 3R) for remainder.

### Close Detection (bar-based)

Evaluated on each bar close using **wick penetration** (conservative):

| Event | BUY condition | SELL condition |
|-------|---------------|----------------|
| SL hit | `bar.low <= current_sl` | `bar.high >= current_sl` |
| TP hit | `bar.high >= current_tp` | `bar.low <= current_tp` |

**Same-bar SL and TP:** SL takes priority (conservative).

**Gap through level:** If `bar.open` is already past SL/TP, close at `bar.open` (simulates gap fill).

```
realized_pnl = remaining_size × (close_price - entry)   # BUY
status = closed; closed_at = bar.open_time
```

Publish `trade.closed` with full PnL (partial + final).

## Configuration

```yaml
position_management:
  breakeven_at_r: 1.0
  trailing:
    enabled: true
    method: atr
    atr_multiplier: 1.5
  partial_exit:
    enabled: true
    percent: 50
    at_r: 1.5
  tp2_at_r: 3.0
```

## Edge Cases

| Case | Behavior |
|------|----------|
| SL and TP hit same bar | SL wins; close at SL price |
| Gap through SL at open | Close at `bar.open`; reason = "sl_gap" |
| Position already partial | Breakeven not re-triggered; trail on remainder |
| `remaining_size < min_lot` after partial | Close entire remainder |
| No bar received (feed down) | No action; log warning |
| Manual close | `close_position_manual`; market price = bar.close |
| Trailing would widen SL | Reject update (SL only tightens) |

## Acceptance Criteria

- [ ] Open positions monitored on `market_data.bar.received`
- [ ] Breakeven fires once at configured R level
- [ ] ATR trailing only tightens SL
- [ ] Partial exit reduces size and records event
- [ ] SL/TP hit closes position; same-bar → SL priority
- [ ] Gap-through closes at bar open
- [ ] Realized PnL includes partial + final
- [ ] Unit tests per action type with fixture bars
- [ ] Integration test: open → breakeven → trail → close

## Dependencies

- Spec 11 (Execution Engine)
- Spec 02 (Market Data — bar events)
- Spec 06 (SMC — structure trailing, optional)

## Downstream Consumers

- Analytics (Spec 14)
- Trading Journal (Spec 13)
