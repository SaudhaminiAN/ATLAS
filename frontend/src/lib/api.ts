import type { ApiEnvelope } from "../types/api";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

export class ApiClientError extends Error {
  constructor(
    message: string,
    public readonly code: string,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new ApiClientError(`HTTP ${response.status}`, "HTTP_ERROR");
  }
  const body = (await response.json()) as ApiEnvelope<T>;
  if (!body.success || body.data === null) {
    throw new ApiClientError(
      body.error?.message ?? "Request failed",
      body.error?.code ?? "API_ERROR",
    );
  }
  return body.data;
}

export const SYMBOL = "XAUUSD";
export const TIMEFRAME = "M15";

export const endpoints = {
  bars: (symbol: string) =>
    `/api/v1/market-data/${symbol}/bars?timeframe=${TIMEFRAME}&limit=300`,
  latestDecision: (symbol: string) => `/api/v1/decisions/${symbol}/latest`,
  confluence: (symbol: string) => `/api/v1/analysis/${symbol}/confluence`,
  context: (symbol: string) => `/api/v1/analysis/${symbol}/context`,
  mtf: (symbol: string) => `/api/v1/analysis/${symbol}/mtf`,
  validation: (symbol: string) => `/api/v1/analysis/${symbol}/validation`,
  newsStatus: () => `/api/v1/news/status`,
  journal: (symbol: string, limit = 20) =>
    `/api/v1/journal/decisions?symbol=${symbol}&limit=${limit}`,
  health: () => `/api/v1/health`,
  analyticsDecisionStats: (symbol: string) =>
    `/api/v1/analytics/decision-stats?symbol=${symbol}`,
  analyticsModuleAccuracy: (symbol: string) =>
    `/api/v1/analytics/module-accuracy?symbol=${symbol}`,
  analyticsPerformance: (symbol: string) =>
    `/api/v1/analytics/performance?symbol=${symbol}`,
} as const;
