export type Direction = "BUY" | "SELL" | "WAIT";

export interface ApiError {
  code: string;
  message: string;
  details?: unknown[];
}

export interface ApiEnvelope<T> {
  success: boolean;
  data: T | null;
  error: ApiError | null;
  meta: { request_id: string; timestamp: string };
}

export interface OHLCVBar {
  symbol: string;
  timeframe: string;
  open_time: string;
  open: string | number;
  high: string | number;
  low: string | number;
  close: string | number;
  volume: string | number;
  is_outlier: boolean;
  quality_flags: string[];
}

export interface EvidenceItem {
  source: string;
  direction: string;
  weight: string | number;
  score: string | number;
  weighted_contribution: string | number;
  description: string;
}

export interface ModuleScore {
  source: string;
  direction: string;
  score: string | number;
  weight: string | number;
  weighted_contribution: string | number;
}

export interface ConfluenceResult {
  symbol: string;
  suggested_direction: Direction;
  total_score: string | number;
  raw_score: string | number;
  bullish_raw: string | number;
  bearish_raw: string | number;
  news_penalty: string | number;
  module_scores: ModuleScore[];
  evidence: EvidenceItem[];
  evidence_count: number;
  has_conflict: boolean;
  strategy_profile_id: string;
  computed_at: string;
}

export interface ValidationRuleResult {
  rule_name: string;
  passed: boolean;
  reason: string;
  enabled: boolean;
}

export interface ValidationResult {
  symbol: string;
  direction: string;
  is_valid: boolean;
  rules: ValidationRuleResult[];
  failed_rules: string[];
  strategy_profile_id: string;
  validated_at: string;
}

export interface TradingDecision {
  id: string;
  symbol: string;
  direction: Direction;
  is_actionable: boolean;
  confluence_score: string | number;
  strategy_id: string;
  reason: string;
  correlation_id: string;
  decided_at: string;
  confluence_snapshot: ConfluenceResult | null;
  validation_snapshot: ValidationResult | null;
  risk_snapshot: Record<string, unknown> | null;
  news_status: {
    is_blocked: boolean;
    is_soft_downgrade: boolean;
    confluence_penalty: string | number;
    next_event_name: string | null;
    next_event_at: string | null;
    as_of: string;
  } | null;
}

export interface MarketContext {
  symbol: string;
  primary_session: string;
  active_sessions: string[];
  volatility_regime: string;
  spread_status: string;
  structural_bias: string;
  atr_value: string | number;
  atr_percentile: string | number;
  computed_at: string;
}

export interface TimeframeBias {
  timeframe: string;
  bias: string;
  confidence: string | number;
  trend_source: string;
  key_levels: Record<string, unknown>[];
}

export interface MTFAnalysis {
  symbol: string;
  biases: TimeframeBias[];
  alignment_score: string | number;
  dominant_bias: string;
  has_conflict: boolean;
  distant_conflict: boolean;
  aligned: boolean;
  computed_at: string;
}

export interface NewsFilterStatus {
  is_blocked: boolean;
  is_soft_downgrade: boolean;
  confluence_penalty: string | number;
  next_event: { name: string; scheduled_at: string } | null;
  as_of: string;
}

export interface PaginatedDecisions {
  items: TradingDecision[];
  total: number;
  limit: number;
  offset: number;
}

export interface WebSocketMessage<T = unknown> {
  channel: string;
  event: string;
  payload: T;
  timestamp: string;
}

export interface BarWsPayload {
  symbol: string;
  timeframe: string;
  open_time: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
}

export interface DecisionWsPayload {
  id: string;
  symbol: string;
  direction: Direction;
  is_actionable: boolean;
  confluence_score: string;
  reason: string;
  strategy_id: string;
  decided_at: string;
}

export interface WaitReasonCount {
  reason: string;
  count: number;
}

export interface DecisionStats {
  total_decisions: number;
  wait_count: number;
  buy_count: number;
  sell_count: number;
  actionable_count: number;
  wait_rate: string | number;
  actionable_rate: string | number;
  top_wait_reasons: WaitReasonCount[];
}

export interface ModuleAccuracy {
  source: string;
  appearances: number;
  true_positive: number;
  false_signal: number;
  neutral_wait: number;
  true_positive_rate: string | number;
  false_signal_rate: string | number;
}

export interface PerformanceSummary {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: string | number;
  profit_factor: string | number;
  total_pnl: string | number;
  max_drawdown: string | number;
}
