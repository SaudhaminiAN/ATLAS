import type { ApiEnvelope } from "../types/api";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

const STORAGE_ACCESS = "atlas_access_token";
const STORAGE_REFRESH = "atlas_refresh_token";

let accessToken: string | null = null;
let refreshToken: string | null = null;
let refreshInFlight: Promise<boolean> | null = null;

export class ApiClientError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

export function loadStoredTokens(): void {
  accessToken = localStorage.getItem(STORAGE_ACCESS);
  refreshToken = localStorage.getItem(STORAGE_REFRESH);
}

export function setAuthTokens(tokens: { access_token: string; refresh_token: string } | null): void {
  if (tokens) {
    accessToken = tokens.access_token;
    refreshToken = tokens.refresh_token;
    localStorage.setItem(STORAGE_ACCESS, tokens.access_token);
    localStorage.setItem(STORAGE_REFRESH, tokens.refresh_token);
    return;
  }

  accessToken = null;
  refreshToken = null;
  localStorage.removeItem(STORAGE_ACCESS);
  localStorage.removeItem(STORAGE_REFRESH);
}

export function getAccessToken(): string | null {
  return accessToken;
}

function authHeaders(): HeadersInit {
  if (!accessToken) {
    return {};
  }
  return { Authorization: `Bearer ${accessToken}` };
}

async function parseEnvelope<T>(response: Response): Promise<ApiEnvelope<T>> {
  return (await response.json()) as ApiEnvelope<T>;
}

async function refreshAccessToken(): Promise<boolean> {
  if (!refreshToken) {
    return false;
  }
  if (refreshInFlight) {
    return refreshInFlight;
  }

  refreshInFlight = (async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) {
        setAuthTokens(null);
        return false;
      }
      const body = await parseEnvelope<{
        access_token: string;
        refresh_token: string;
      }>(response);
      if (!body.success || !body.data) {
        setAuthTokens(null);
        return false;
      }
      setAuthTokens(body.data);
      return true;
    } catch {
      setAuthTokens(null);
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

async function request(
  path: string,
  init: RequestInit = {},
  retryOnUnauthorized = true,
): Promise<Response> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...authHeaders(),
      ...init.headers,
    },
  });

  if (response.status === 401 && retryOnUnauthorized && refreshToken) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return request(path, init, false);
    }
  }

  return response;
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await request(path);
  if (!response.ok) {
    throw new ApiClientError(`HTTP ${response.status}`, "HTTP_ERROR", response.status);
  }
  const body = await parseEnvelope<T>(response);
  if (!body.success || body.data === null) {
    throw new ApiClientError(
      body.error?.message ?? "Request failed",
      body.error?.code ?? "API_ERROR",
      response.status,
    );
  }
  return body.data;
}

/** GET that returns null when the API responds with success: false (e.g. NOT_FOUND). */
export async function apiGetOptional<T>(path: string): Promise<T | null> {
  const response = await request(path);
  if (!response.ok) {
    throw new ApiClientError(`HTTP ${response.status}`, "HTTP_ERROR", response.status);
  }
  const body = await parseEnvelope<T>(response);
  if (!body.success || body.data === null) {
    return null;
  }
  return body.data;
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const response = await request(path, {
    method: "POST",
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const parsed = (await response.json().catch(() => null)) as ApiEnvelope<T> | null;
    throw new ApiClientError(
      parsed?.error?.message ?? `HTTP ${response.status}`,
      parsed?.error?.code ?? "HTTP_ERROR",
      response.status,
    );
  }
  const envelope = await parseEnvelope<T>(response);
  if (!envelope.success || envelope.data === null) {
    throw new ApiClientError(
      envelope.error?.message ?? "Request failed",
      envelope.error?.code ?? "API_ERROR",
      response.status,
    );
  }
  return envelope.data;
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
  authLogin: () => `/api/v1/auth/login`,
  authRegister: () => `/api/v1/auth/register`,
  authMe: () => `/api/v1/auth/me`,
  analyticsDecisionStats: (symbol: string) =>
    `/api/v1/analytics/decision-stats?symbol=${symbol}`,
  analyticsModuleAccuracy: (symbol: string) =>
    `/api/v1/analytics/module-accuracy?symbol=${symbol}`,
  analyticsPerformance: (symbol: string) =>
    `/api/v1/analytics/performance?symbol=${symbol}`,
  explanation: (decisionId: string) => `/api/v1/explanations/${decisionId}`,
  trades: (symbol: string, limit = 20) =>
    `/api/v1/trades?symbol=${symbol}&limit=${limit}`,
} as const;
