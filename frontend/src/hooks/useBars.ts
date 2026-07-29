import { useCallback, useEffect, useState } from "react";
import { apiGet, endpoints, SYMBOL } from "../lib/api";
import { toNumber } from "../lib/format";
import type { BarWsPayload, OHLCVBar } from "../types/api";
import { useWebSocket } from "./useWebSocket";

export interface ChartBar {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

function barToChart(bar: OHLCVBar | BarWsPayload): ChartBar {
  return {
    time: Math.floor(new Date(bar.open_time).getTime() / 1000),
    open: toNumber(bar.open),
    high: toNumber(bar.high),
    low: toNumber(bar.low),
    close: toNumber(bar.close),
  };
}

export function useBars(symbol = SYMBOL) {
  const [bars, setBars] = useState<ChartBar[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadBars = useCallback(async () => {
    try {
      const data = await apiGet<OHLCVBar[]>(endpoints.bars(symbol));
      setBars(data.map(barToChart).sort((a, b) => a.time - b.time));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load bars");
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => {
    void loadBars();
  }, [loadBars]);

  const onBar = useCallback((payload: BarWsPayload) => {
    if (payload.symbol !== symbol) return;
    const next = barToChart(payload);
    setBars((prev) => {
      const idx = prev.findIndex((b) => b.time === next.time);
      if (idx >= 0) {
        const copy = [...prev];
        copy[idx] = next;
        return copy;
      }
      return [...prev, next].sort((a, b) => a.time - b.time);
    });
  }, [symbol]);

  const { status: wsStatus } = useWebSocket<BarWsPayload>({
    channel: `market.${symbol}.bars`,
    onMessage: onBar,
  });

  return { bars, loading, error, wsStatus, reload: loadBars };
}
