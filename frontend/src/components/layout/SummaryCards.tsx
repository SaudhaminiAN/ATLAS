import type { TradingDecision } from "../../types/api";
import type { ChartBar } from "../../hooks/useBars";
import { formatScore } from "../../lib/format";

interface SummaryCardsProps {
  bars: ChartBar[];
  decision: TradingDecision | null;
  loading?: boolean;
}

export function SummaryCards({ bars, decision, loading }: SummaryCardsProps) {
  const last = bars.length > 0 ? bars[bars.length - 1] : null;
  const direction = decision?.direction ?? "WAIT";
  const reason = decision?.reason ?? "Waiting for first analysis run…";

  const signalColor =
    direction === "BUY"
      ? "text-emerald-400 border-emerald-500/40 bg-emerald-500/10"
      : direction === "SELL"
        ? "text-red-400 border-red-500/40 bg-red-500/10"
        : "text-zinc-400 border-zinc-600/40 bg-zinc-800/40";

  if (loading && !decision) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="skeleton h-24 rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <MetricCard
        label="Last price (demo)"
        value={last ? last.close.toFixed(2) : "—"}
        sub={last ? `O ${last.open.toFixed(2)} · H ${last.high.toFixed(2)} · L ${last.low.toFixed(2)}` : `${bars.length} bars loaded`}
        accent="text-white"
      />
      <MetricCard
        label="Trading signal"
        value={direction}
        sub={decision?.is_actionable ? "Ready to act" : "Do not trade"}
        accent={signalColor}
        large
      />
      <MetricCard
        label="Confidence score"
        value={decision ? formatScore(decision.confluence_score) : "—"}
        sub="How strong the evidence is"
        accent="text-amber-400"
      />
      <MetricCard
        label="Why this signal?"
        value=""
        sub={reason}
        accent="text-zinc-300"
        multiline
      />
    </div>
  );
}

function MetricCard({
  label,
  value,
  sub,
  accent,
  large,
  multiline,
}: {
  label: string;
  value: string;
  sub: string;
  accent: string;
  large?: boolean;
  multiline?: boolean;
}) {
  return (
    <div className={`rounded-xl border p-4 ${large ? accent : "border-zinc-800 bg-zinc-900/80"}`}>
      <p className="text-[11px] uppercase tracking-wider text-zinc-500 mb-2">{label}</p>
      {!multiline && value && (
        <p className={`font-mono font-bold ${large ? "text-3xl" : "text-xl"} ${large ? "" : accent}`}>
          {value}
        </p>
      )}
      <p
        className={`${multiline ? "text-sm leading-relaxed" : "text-xs mt-1"} ${multiline ? accent : "text-zinc-400"}`}
      >
        {sub}
      </p>
    </div>
  );
}
