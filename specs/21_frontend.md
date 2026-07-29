# Spec 21 — Frontend (Analysis Platform UI)

## Objective

React dashboard to visualize analysis, decisions, and performance.

## Scope

### In Scope

- Chart, analysis panel, decision history, analytics (phased)
- WebSocket live updates
- TypeScript API client with strict types

### Out of Scope

- Mobile app, order placement UI, custom indicators

## Inputs (from API)

| Endpoint / Channel | Data | Phase |
|--------------------|------|-------|
| `GET /market-data/{symbol}/bars` | OHLCV | 1 |
| `GET /decisions/{symbol}/latest` | Decision | 1 |
| `GET /analysis/{symbol}/confluence` | Confluence breakdown | 1 |
| `GET /analysis/{symbol}/context` | Market context | 1 |
| `GET /news/status` | News filter | 1 |
| `ws: market.{symbol}.bars` | Live bars | 1 |
| `ws: decisions.{symbol}` | Live decisions | 1 |
| `GET /analytics/*` | Metrics | 2 |
| Chart overlays from analysis API | Levels, OB, FVG | 2 |

## Outputs

| Output | Type |
|--------|------|
| Rendered UI | React components |
| User filters | Query params to API |

## TypeScript API Types

```typescript
// src/types/api.ts

export type Direction = "BUY" | "SELL" | "WAIT";
export type Bias = "bullish" | "bearish" | "neutral";

export interface ApiEnvelope<T> {
  success: boolean;
  data: T | null;
  error: ApiError | null;
  meta: { request_id: string; timestamp: string };
}

export interface OHLCVBar {
  open_time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface EvidenceItem {
  source: string;
  direction: Direction;
  weight: number;
  score: number;
  weighted_contribution: number;
  description: string;
}

export interface ConfluenceResult {
  suggested_direction: Direction;
  total_score: number;
  evidence: EvidenceItem[];
  evidence_count: number;
  has_conflict: boolean;
}

export interface ValidationRuleResult {
  rule_name: string;
  passed: boolean;
  reason: string;
  enabled: boolean;
}

export interface TradingDecision {
  id: string;
  direction: Direction;
  is_actionable: boolean;
  confluence_score: number;
  reason: string;
  confluence_snapshot: ConfluenceResult;
  validation_snapshot: { is_valid: boolean; rules: ValidationRuleResult[] };
  decided_at: string;
}

export interface MarketContext {
  primary_session: string;
  volatility_regime: string;
  structural_bias: Bias;
  atr_value: number;
}

export interface MTFAnalysis {
  biases: Array<{ timeframe: string; bias: Bias; confidence: number }>;
  alignment_score: number;
  has_conflict: boolean;
  aligned: boolean;
}

export interface NewsFilterStatus {
  is_blocked: boolean;
  is_soft_downgrade: boolean;
  confluence_penalty: number;
  next_event: { name: string; scheduled_at: string } | null;
}

export interface WebSocketMessage<T = unknown> {
  channel: string;
  event: string;
  payload: T;
  timestamp: string;
}
```

## Key Components

(See directory tree in prior version.)

## Edge Cases (UI)

| Case | Behavior |
|------|----------|
| API timeout | Retry button + error toast |
| WebSocket disconnect | Auto-reconnect with backoff; stale indicator |
| Empty chart (no bars) | Empty state message |
| Loading | Skeleton placeholders |
| Decision WAIT | Show reason prominently (not hidden) |

## MVP Frontend (Phase 1)

- [ ] Chart + live bars
- [ ] Analysis panel (decision, confluence, validation, MTF, news)
- [ ] Decision history

Defer Phase 2: overlays, analytics dashboard. Phase 3: AI explanation panel.

## Acceptance Criteria

- [ ] Types in `src/types/api.ts` match OpenAPI schema
- [ ] No `any` in API layer (strict TypeScript)
- [ ] WebSocket reconnect
- [ ] Loading/error/empty states
- [ ] Confluence UI matches API exactly

## Dependencies

- Spec 01, 02, 17, 20; Spec 14 (Phase 2)

## Notes

See `docs/mvp_roadmap.md` for phased delivery.
