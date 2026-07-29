import { RefreshCw } from "lucide-react";
import { formatScore, formatTime } from "../../lib/format";
import type { TradingDecision } from "../../types/api";
import { DirectionBadge } from "../ui/DirectionBadge";

interface DecisionHeroProps {
  decision: TradingDecision | null;
  loading?: boolean;
  onRefresh?: () => void;
}

const glow: Record<string, string> = {
  BUY: "shadow-[0_0_60px_-12px_rgba(52,211,153,0.35)] border-buy/40",
  SELL: "shadow-[0_0_60px_-12px_rgba(248,113,113,0.35)] border-sell/40",
  WAIT: "shadow-[0_0_40px_-12px_rgba(113,113,122,0.2)] border-wait/30",
};

const textColor: Record<string, string> = {
  BUY: "text-buy",
  SELL: "text-sell",
  WAIT: "text-wait",
};

export function DecisionHero({ decision, loading, onRefresh }: DecisionHeroProps) {
  if (loading && !decision) {
    return (
      <div className="glass-panel rounded-2xl p-8 space-y-4">
        <div className="skeleton h-4 w-24" />
        <div className="skeleton h-16 w-40" />
        <div className="skeleton h-4 w-full" />
      </div>
    );
  }

  if (!decision) {
    return (
      <div className="glass-panel rounded-2xl p-8 text-center">
        <p className="text-muted text-sm">No decision yet — waiting for pipeline</p>
        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            className="mt-4 text-gold text-sm hover:text-gold-glow transition-colors"
          >
            Refresh
          </button>
        )}
      </div>
    );
  }

  const dir = decision.direction;

  return (
    <div
      className={`relative glass-panel rounded-2xl p-6 border-2 transition-all duration-500 ${glow[dir]}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-mono tracking-[0.25em] uppercase text-muted mb-2">
            Signal
          </p>
          <div className="flex items-center gap-4">
            <span
              className={`font-display text-6xl font-extrabold tracking-tight ${textColor[dir]}`}
            >
              {dir}
            </span>
            <DirectionBadge direction={dir} />
          </div>
        </div>
        <div className="text-right">
          <p className="text-xs text-muted font-mono mb-1">Confluence</p>
          <p className="text-2xl font-mono font-semibold text-gold">
            {formatScore(decision.confluence_score)}
          </p>
        </div>
      </div>

      <div className="mt-5 pt-5 border-t border-border/60">
        <p className="text-sm text-white/90 leading-relaxed">{decision.reason}</p>
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs font-mono text-muted">
          <span>{formatTime(decision.decided_at)}</span>
          <span className="text-border">·</span>
          <span title={decision.correlation_id}>
            {decision.correlation_id.slice(0, 12)}…
          </span>
          {decision.is_actionable && (
            <>
              <span className="text-border">·</span>
              <span className="text-buy">Actionable</span>
            </>
          )}
        </div>
      </div>

      {onRefresh && (
        <button
          type="button"
          onClick={onRefresh}
          className="absolute top-4 right-4 p-2 rounded-lg text-muted hover:text-gold hover:bg-elevated transition-colors"
          aria-label="Refresh"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
