# ATLAS Accuracy Principles

## Definition of "Accurate" in ATLAS

Accurate analysis means:

1. **Reproducible** — same bars in → same decision out, every time
2. **Evidence-based** — every non-WAIT decision cites ≥3 independent evidence sources
3. **Conservative** — correctly rejects weak setups (low false-positive rate matters more than high trade count)
4. **Measurable** — accuracy tracked via backtests and module-level false-signal rates
5. **No look-ahead** — live and backtest use identical bar access rules

Accuracy is **not** defined as "predicts price correctly every time." No system can guarantee that.

## Data Quality Requirements

All analysis accuracy depends on clean input data (see Spec 02):

| Rule | Requirement |
|------|-------------|
| Bar integrity | `high >= max(open, close)`, `low <= min(open, close)`, all prices > 0 |
| Timezone | All bars stored and processed in UTC |
| Bar alignment | Higher-TF bars use broker-standard close times (e.g. H1 at :00 UTC) |
| Closed bars only | Analysis runs on bar **close**, never on forming candles |
| Gap handling | Missing bars logged; pipeline skips or interpolates per config (never silently ignore) |
| Duplicate prevention | Unique constraint on `(instrument, timeframe, open_time)` |
| Outlier rejection | Bars with range > 5× ATR flagged and excluded from analysis |

## Deterministic Rule Definitions

Subjective concepts (SMC, price action) must use **exact numeric rules** defined in specs 05–07. Implementations must match spec definitions — not trader discretion.

Examples:

- Order block = last opposing candle before displacement ≥ 1.5× ATR
- Pin bar = wick ≥ 2/3 of range AND body ≤ 1/3 of range
- Equal highs = two swing highs within 0.1% price tolerance

See updated Specs 06 and 07 for full rule tables.

## Confluence Thresholds

Default conservative thresholds (override via Strategy Engine):

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| Min confluence score | 0.70 | High bar reduces false signals |
| Min evidence sources | 3 | Prevents single-module signals |
| MTF alignment minimum | 0.75 | Higher-TF agreement required |
| Min R:R potential | 1:2 | Rejects poor reward setups |
| Volatility extreme | ATR > 95th percentile (Spec 03) | Blocks via `volatility_check` (Spec 09) |

Per-module confluence scoring is defined in Spec 08 — implementations must not invent alternate formulas.

## Module Accuracy Tracking

Analytics module (Spec 14) tracks per-module contribution quality:

- **True positive rate** — evidence source present on winning trades
- **False signal rate** — evidence source present on losing trades or rejected setups that would have lost
- **WAIT correctness** — blocked setups that would have hit SL before TP

Review module accuracy monthly and adjust Strategy Engine weights — not code.

## Backtest Integrity

Backtests (Spec 16) must guarantee:

- Bars processed in strict chronological order
- Each pipeline stage sees only data available at that bar's close time
- Same Strategy Profile and validation rules as live
- Results include decision count, WAIT rate, and win rate separately

A backtest that looks profitable but uses look-ahead data is worse than no backtest.

## AI and Accuracy

The AI Explanation layer (Spec 15) does not affect accuracy. It describes decisions already made. Guardrails prevent the LLM from:

- Predicting future prices
- Claiming guaranteed profitability
- Suggesting rule overrides

## Review Cadence

| Activity | Frequency |
|----------|-----------|
| Backtest on rolling 6-month window | Weekly during development |
| Module false-signal rate review | Monthly |
| Strategy profile weight adjustment | After ≥100 decisions or 30 days |
| Data quality audit (gaps, outliers) | Weekly |
