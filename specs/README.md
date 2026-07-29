# ATLAS Module Specifications

22 documents: template + 21 module specs. Implement **one at a time** per `docs/mvp_roadmap.md`.

## Spec Template

All specs follow [`00_spec_template.md`](00_spec_template.md): Inputs, Outputs, Interfaces, Database, Edge Cases, Acceptance Criteria.

## Phase 1 — Analysis MVP

| Spec | Module |
|------|--------|
| [01](01_project_setup.md) | Project Setup |
| [02](02_market_data.md) | Market Data |
| [18](18_strategy_engine.md) | Strategy Engine |
| [19](19_news_filter.md) | News Filter |
| [03](03_market_context.md) | Market Context |
| [04](04_timeframe.md) | Multi-TF Analysis |
| [05](05_technical_analysis.md) | Technical Analysis |
| [06](06_smc.md) | SMC |
| [07](07_price_action.md) | Price Action |
| [08](08_confluence.md) | Confluence |
| [09](09_validation.md) | Validation |
| [20](20_analysis_pipeline.md) | Analysis Pipeline |
| [17](17_decision_engine.md) | Decision Engine |
| [13](13_journal.md) | Journal (decisions) |
| [21](21_frontend.md) | Frontend MVP |

## Phase 2 — Measure Accuracy

| Spec | Module |
|------|--------|
| [16](16_backtesting.md) | Backtesting |
| [14](14_analytics.md) | Analytics |
| [21](21_frontend.md) | Frontend Phase 2 |

## Phase 3 — Execution & AI

| Spec | Module |
|------|--------|
| [10](10_risk.md) | Risk Management |
| [11](11_execution.md) | Execution |
| [12](12_position_management.md) | Position Management |
| [13](13_journal.md) | Journal (full) |
| [15](15_ai.md) | AI Explanation |

## Cross-References

- [Accuracy Principles](../docs/accuracy_principles.md)
- [Architecture](../docs/architecture.md)
- [Database Design](../docs/database_design.md)
- [MVP Roadmap](../docs/mvp_roadmap.md)

## Review Status

All specs updated with standardized sections (2026-07-29). Key fixes:

- Spec 08: per-module confluence score mapping
- Spec 09: `minimum_rr_potential`, `session_check`, volatility aligned to 95th percentile
- Spec 12: full domain models and position rules
- Spec 02/16: `MarketDataReplayProtocol`
- Spec 14: module accuracy formulas
- Spec 21: TypeScript API types
