import { formatScore, formatSession, capitalize } from "../../lib/format";
import type { MarketContext, MTFAnalysis } from "../../types/api";
import { Card } from "../ui/Card";

function BiasPill({ bias }: { bias: string }) {
  const color =
    bias === "bullish"
      ? "text-buy bg-buy/10 border-buy/20"
      : bias === "bearish"
        ? "text-sell bg-sell/10 border-sell/20"
        : "text-wait bg-wait/10 border-wait/20";
  return (
    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${color}`}>
      {capitalize(bias)}
    </span>
  );
}

export function ContextPanel({
  context,
  mtf,
}: {
  context: MarketContext | null;
  mtf: MTFAnalysis | null;
}) {
  return (
    <Card title="Market Context">
      {!context && !mtf ? (
        <p className="text-sm text-muted">No context data</p>
      ) : (
        <div className="space-y-4">
          {context && (
            <div className="grid grid-cols-2 gap-3">
              <Metric label="Session" value={formatSession(context.primary_session)} />
              <Metric label="Volatility" value={capitalize(context.volatility_regime)} />
              <Metric label="Bias" value={capitalize(context.structural_bias)} />
              <Metric label="ATR" value={String(context.atr_value)} />
            </div>
          )}
          {mtf && (
            <div className="pt-3 border-t border-border/50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-muted font-mono">MTF Alignment</span>
                <span className="text-sm font-mono font-semibold text-gold">
                  {formatScore(mtf.alignment_score)}
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {mtf.biases.map((b) => (
                  <div
                    key={b.timeframe}
                    className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-elevated border border-border/40"
                  >
                    <span className="text-[10px] font-mono text-muted">{b.timeframe}</span>
                    <BiasPill bias={b.bias} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-2.5 rounded-lg bg-elevated/50 border border-border/30">
      <p className="text-[10px] font-mono uppercase tracking-wider text-muted mb-0.5">{label}</p>
      <p className="text-sm font-medium text-white/90">{value}</p>
    </div>
  );
}
