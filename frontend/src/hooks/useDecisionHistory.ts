import { useCallback, useEffect, useState } from "react";
import { apiGet, endpoints, SYMBOL } from "../lib/api";
import type { PaginatedDecisions } from "../types/api";

export function useDecisionHistory(symbol = SYMBOL, limit = 20) {
  const [history, setHistory] = useState<PaginatedDecisions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await apiGet<PaginatedDecisions>(endpoints.journal(symbol, limit));
      setHistory(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load history");
    } finally {
      setLoading(false);
    }
  }, [symbol, limit]);

  useEffect(() => {
    void load();
  }, [load]);

  return { history, loading, error, reload: load };
}
