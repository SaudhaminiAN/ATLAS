import { useEffect, useRef } from "react";
import {
  CandlestickSeries,
  ColorType,
  createChart,
  type IChartApi,
  type ISeriesApi,
} from "lightweight-charts";
import type { ChartBar } from "../../hooks/useBars";

interface PriceChartProps {
  bars: ChartBar[];
  loading?: boolean;
}

export function PriceChart({ bars, loading }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#6b6b7b",
        fontFamily: "IBM Plex Mono, monospace",
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)" },
        horzLines: { color: "rgba(255,255,255,0.04)" },
      },
      rightPriceScale: {
        borderColor: "rgba(255,255,255,0.06)",
      },
      timeScale: {
        borderColor: "rgba(255,255,255,0.06)",
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: {
        vertLine: { color: "rgba(232,197,71,0.4)", labelBackgroundColor: "#e8c547" },
        horzLine: { color: "rgba(232,197,71,0.4)", labelBackgroundColor: "#e8c547" },
      },
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#34d399",
      downColor: "#f87171",
      borderUpColor: "#34d399",
      borderDownColor: "#f87171",
      wickUpColor: "#34d399",
      wickDownColor: "#f87171",
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        chart.applyOptions({ width: entry.contentRect.width, height: entry.contentRect.height });
      }
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!seriesRef.current || bars.length === 0) return;
    seriesRef.current.setData(
      bars.map((b) => ({
        time: b.time as unknown as import("lightweight-charts").UTCTimestamp,
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      })),
    );
    chartRef.current?.timeScale().fitContent();
  }, [bars]);

  return (
    <div className="relative h-full min-h-[420px]">
      {loading && bars.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center z-10">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-gold/30 border-t-gold rounded-full animate-spin" />
            <span className="text-sm text-muted font-mono">Loading chart…</span>
          </div>
        </div>
      )}
      {!loading && bars.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center">
          <p className="text-muted text-sm">No bar data yet — start the backend mock stream</p>
        </div>
      )}
      <div ref={containerRef} className="absolute inset-0" />
    </div>
  );
}
