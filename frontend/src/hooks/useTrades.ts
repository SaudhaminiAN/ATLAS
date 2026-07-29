import { useCallback, useEffect, useState } from "react";
import { apiGet, endpoints, SYMBOL } from "../lib/api";
import type { Trade } from "../types/api";

interface TradesState {
  trades: Trade[];
  loading: boolean;
  error: string | null;
}

const initial: TradesState = {
  trades: [],
  loading: true,
  error: null,
};

export function useTrades(symbol = SYMBOL, limit = 20) {
  const [state, setState] = useState<TradesState>(initial);

  const refresh = useCallback(async () => {
    setState((s) => ({ ...s, loading: s.trades.length === 0, error: null }));
    try {
      const trades = await apiGet<Trade[]>(endpoints.trades(symbol, limit));
      setState({ trades, loading: false, error: null });
    } catch (err) {
      setState((s) => ({
        ...s,
        loading: false,
        error: err instanceof Error ? err.message : "Failed to load trades",
      }));
    }
  }, [symbol, limit]);

  useEffect(() => {
    void refresh();
    const interval = setInterval(() => void refresh(), 30_000);
    return () => clearInterval(interval);
  }, [refresh]);

  const openCount = state.trades.filter(
    (t) => t.status === "open" || t.status === "partial",
  ).length;

  const closedPnl = state.trades
    .filter((t) => t.status === "closed" && t.realized_pnl !== null)
    .reduce((sum, t) => sum + Number(t.realized_pnl), 0);

  return { ...state, refresh, openCount, closedPnl };
}
