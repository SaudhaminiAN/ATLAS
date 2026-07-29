import type { ChartBar } from "../../hooks/useBars";
import { PriceChart } from "./PriceChart";

interface ChartPanelProps {
  bars: ChartBar[];
  loading?: boolean;
}

export function ChartPanel({ bars, loading }: ChartPanelProps) {
  const last = bars.length > 0 ? bars[bars.length - 1] : null;

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/80 overflow-hidden min-h-[520px] flex flex-col">
      <div className="px-5 py-4 border-b border-zinc-800 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-white">Gold price chart</h2>
          <p className="text-sm text-zinc-500 mt-0.5">
            XAUUSD · 15-minute candles · {bars.length} bars shown
          </p>
        </div>
        {last && (
          <div className="flex gap-6 text-sm font-mono">
            <OHLC label="Open" value={last.open} />
            <OHLC label="High" value={last.high} positive />
            <OHLC label="Low" value={last.low} negative />
            <OHLC label="Close" value={last.close} highlight />
          </div>
        )}
      </div>
      <div className="flex-1 p-3 min-h-[440px]">
        <PriceChart bars={bars} loading={loading} />
      </div>
      <div className="px-5 py-3 border-t border-zinc-800 bg-zinc-950/50 text-xs text-zinc-500">
        <span className="text-emerald-500">Green</span> = price went up ·{" "}
        <span className="text-red-400">Red</span> = price went down · Each candle = 15 minutes
      </div>
    </div>
  );
}

function OHLC({
  label,
  value,
  positive,
  negative,
  highlight,
}: {
  label: string;
  value: number;
  positive?: boolean;
  negative?: boolean;
  highlight?: boolean;
}) {
  const color = highlight
    ? "text-amber-400"
    : positive
      ? "text-emerald-400"
      : negative
        ? "text-red-400"
        : "text-zinc-400";
  return (
    <div>
      <span className="text-zinc-600 text-[10px] uppercase block">{label}</span>
      <span className={color}>{value.toFixed(2)}</span>
    </div>
  );
}
