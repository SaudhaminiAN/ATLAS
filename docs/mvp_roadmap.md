# ATLAS MVP Roadmap

## Goal

Deliver a **working, measurable analysis platform** as early as possible — then layer execution, AI, and full analytics on proven analysis quality.

## Phases

### Phase 1 — Analysis MVP (Specs 01–09, 17–21)

**Outcome:** Live XAUUSD analysis with BUY/SELL/WAIT decisions, visible on dashboard, measurable via paper decisions journal.

| Order | Spec | Deliverable |
|-------|------|-------------|
| 1 | 01 Project Setup | Backend, frontend scaffold, Docker, event bus |
| 2 | 02 Market Data | OHLCV ingest, validation, WebSocket bars |
| 3 | 18 Strategy Engine | Default conservative profile |
| 4 | 19 News Filter | Block windows, mock calendar |
| 5 | 03 Market Context | Session, volatility, bias |
| 6 | 04 Multi-TF Analysis | Alignment score, conflict detection |
| 7 | 05 Technical Analysis | S/R, trend, indicator context |
| 8 | 06 SMC | BOS/CHoCH, OB, liquidity, FVG |
| 9 | 07 Price Action | Patterns at key levels |
| 10 | 08 Confluence | Weighted evidence scoring |
| 11 | 09 Validation | Deterministic rule engine |
| 12 | 20 Analysis Pipeline | End-to-end orchestrator |
| 13 | 17 Decision Engine | Final BUY/SELL/WAIT |
| 14 | 13 Journal (partial) | Persist decisions only (no trades yet) |
| 15 | 21 Frontend (MVP) | Chart + analysis panel + decision history |

**MVP exit criteria:**

- [ ] Pipeline runs on each M15 bar close without error
- [ ] Decisions visible on dashboard within 5s of bar close
- [ ] Every WAIT decision has a logged reason
- [ ] News filter blocks decisions during fixture high-impact events
- [ ] Manual review: 20 consecutive decisions have sensible evidence

---

### Phase 2 — Measure Accuracy (Specs 14, 16, 21 Phase 2)

**Outcome:** Quantified analysis quality via backtesting and module-level metrics.

| Order | Spec | Deliverable |
|-------|------|-------------|
| 1 | 16 Backtesting | Historical replay, no look-ahead |
| 2 | 14 Analytics | Win rate, profit factor, module accuracy |
| 3 | 21 Frontend Phase 2 | Analytics dashboard, chart overlays |

**Phase 2 exit criteria:**

- [ ] Backtest on 6 months XAUUSD M15 data completes without error
- [ ] Module false-signal rates computed per evidence source
- [ ] Win rate and avg R documented in analytics dashboard
- [ ] Backtest results match live pipeline (same rules, same output)

---

### Phase 3 — Execution & AI (Specs 10–12, 15)

**Outcome:** Paper trading with full lifecycle management and AI explanations.

| Order | Spec | Deliverable |
|-------|------|-------------|
| 1 | 10 Risk Management | Position sizing, SL/TP |
| 2 | 11 Execution Engine | Paper trading mode |
| 3 | 12 Position Management | Breakeven, trailing, partial exits |
| 4 | 13 Journal (full) | Trade lifecycle records |
| 5 | 15 AI Explanation | LLM decision summaries |

**Phase 3 exit criteria:**

- [ ] Paper trades executed on actionable decisions
- [ ] Full trade lifecycle journaled
- [ ] AI explanation generated for each decision (mock LLM in CI)
- [ ] 30-day paper trading run with analytics report

---

### Phase 4 — Production Hardening

- Live broker adapter (optional, gated)
- Authentication and user management
- CI/CD pipeline
- Monitoring and alerting
- Production Docker Compose deployment

## Principles

1. **Measure before executing** — prove analysis quality in Phase 2 before paper/live trading
2. **One spec at a time** — complete and test each spec before starting the next
3. **WAIT is success** — a system that correctly waits is better than one that over-trades
4. **Same code for live and backtest** — Analysis Pipeline orchestrator reused in both modes
