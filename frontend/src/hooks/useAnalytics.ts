import { useCallback, useEffect, useState } from "react";
import { apiGet, endpoints, SYMBOL } from "../lib/api";
import type { DecisionStats, ModuleAccuracy, PerformanceSummary } from "../types/api";

interface AnalyticsState {
  decisionStats: DecisionStats | null;
  moduleAccuracy: ModuleAccuracy[];
  performance: PerformanceSummary | null;
  loading: boolean;
  error: string | null;
}

const initial: AnalyticsState = {
  decisionStats: null,
  moduleAccuracy: [],
  performance: null,
  loading: true,
  error: null,
};

export function useAnalytics(symbol = SYMBOL) {
  const [state, setState] = useState<AnalyticsState>(initial);

  const refresh = useCallback(async () => {
    setState((s) => ({
      ...s,
      loading: s.decisionStats === null,
      error: null,
    }));
    try {
      const [decisionStats, moduleAccuracy, performance] = await Promise.all([
        apiGet<DecisionStats>(endpoints.analyticsDecisionStats(symbol)),
        apiGet<ModuleAccuracy[]>(endpoints.analyticsModuleAccuracy(symbol)),
        apiGet<PerformanceSummary>(endpoints.analyticsPerformance(symbol)),
      ]);
      setState({
        decisionStats,
        moduleAccuracy,
        performance,
        loading: false,
        error: null,
      });
    } catch (err) {
      setState((s) => ({
        ...s,
        loading: false,
        error: err instanceof Error ? err.message : "Failed to load analytics",
      }));
    }
  }, [symbol]);

  useEffect(() => {
    void refresh();
    const interval = setInterval(() => void refresh(), 60_000);
    return () => clearInterval(interval);
  }, [refresh]);

  return { ...state, refresh };
}
