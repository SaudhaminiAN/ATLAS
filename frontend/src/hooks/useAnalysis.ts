import { useCallback, useEffect, useState } from "react";
import { apiGet, endpoints, SYMBOL } from "../lib/api";
import type {
  ConfluenceResult,
  MarketContext,
  MTFAnalysis,
  NewsFilterStatus,
  TradingDecision,
  ValidationResult,
} from "../types/api";

interface AnalysisState {
  decision: TradingDecision | null;
  confluence: ConfluenceResult | null;
  context: MarketContext | null;
  mtf: MTFAnalysis | null;
  validation: ValidationResult | null;
  news: NewsFilterStatus | null;
  loading: boolean;
  error: string | null;
}

const initial: AnalysisState = {
  decision: null,
  confluence: null,
  context: null,
  mtf: null,
  validation: null,
  news: null,
  loading: true,
  error: null,
};

export function useAnalysis(symbol = SYMBOL) {
  const [state, setState] = useState<AnalysisState>(initial);

  const refresh = useCallback(async () => {
    setState((s) => ({ ...s, loading: s.decision === null, error: null }));
    try {
      const [decision, confluence, context, mtf, validation, news] =
        await Promise.allSettled([
          apiGet<TradingDecision>(endpoints.latestDecision(symbol)),
          apiGet<ConfluenceResult>(endpoints.confluence(symbol)),
          apiGet<MarketContext>(endpoints.context(symbol)),
          apiGet<MTFAnalysis>(endpoints.mtf(symbol)),
          apiGet<ValidationResult>(endpoints.validation(symbol)),
          apiGet<NewsFilterStatus>(endpoints.newsStatus()),
        ]);

      setState({
        decision: decision.status === "fulfilled" ? decision.value : null,
        confluence: confluence.status === "fulfilled" ? confluence.value : null,
        context: context.status === "fulfilled" ? context.value : null,
        mtf: mtf.status === "fulfilled" ? mtf.value : null,
        validation: validation.status === "fulfilled" ? validation.value : null,
        news: news.status === "fulfilled" ? news.value : null,
        loading: false,
        error: null,
      });
    } catch (err) {
      setState((s) => ({
        ...s,
        loading: false,
        error: err instanceof Error ? err.message : "Failed to load analysis",
      }));
    }
  }, [symbol]);

  useEffect(() => {
    void refresh();
    const interval = setInterval(() => void refresh(), 30_000);
    return () => clearInterval(interval);
  }, [refresh]);

  return { ...state, refresh };
}
