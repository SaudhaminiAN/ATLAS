import { formatScore, formatTime } from "../../lib/format";
import type { TradingDecision } from "../../types/api";
import { DirectionBadge } from "../ui/DirectionBadge";
import { Card } from "../ui/Card";

interface DecisionHistoryProps {
  items: TradingDecision[];
  loading?: boolean;
  total?: number;
}

export function DecisionHistory({ items, loading, total = 0 }: DecisionHistoryProps) {
  return (
    <Card title="Decision Journal">
      <p className="text-xs font-mono text-muted mb-4">{total} total records</p>

      {loading && items.length === 0 ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-14 w-full" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <p className="text-sm text-muted text-center py-8">No decisions recorded yet</p>
      ) : (
        <div className="overflow-x-auto -mx-1">
          <table className="w-full text-left">
            <thead>
              <tr className="text-[10px] font-mono uppercase tracking-wider text-muted border-b border-border/60">
                <th className="pb-3 pl-1 font-medium">Time</th>
                <th className="pb-3 font-medium">Signal</th>
                <th className="pb-3 font-medium">Score</th>
                <th className="pb-3 font-medium">Reason</th>
                <th className="pb-3 pr-1 font-medium">Trace</th>
              </tr>
            </thead>
            <tbody>
              {items.map((d) => (
                <tr
                  key={d.id}
                  className="border-b border-border/30 hover:bg-elevated/30 transition-colors group"
                >
                  <td className="py-3 pl-1 text-xs font-mono text-muted whitespace-nowrap">
                    {formatTime(d.decided_at)}
                  </td>
                  <td className="py-3">
                    <DirectionBadge direction={d.direction} />
                  </td>
                  <td className="py-3 text-xs font-mono text-gold">
                    {formatScore(d.confluence_score)}
                  </td>
                  <td className="py-3 text-xs text-white/80 max-w-xs truncate group-hover:whitespace-normal group-hover:max-w-none">
                    {d.reason}
                  </td>
                  <td className="py-3 pr-1 text-[10px] font-mono text-muted">
                    {d.correlation_id.slice(0, 8)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
