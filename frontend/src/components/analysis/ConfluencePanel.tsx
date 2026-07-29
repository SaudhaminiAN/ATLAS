import { formatScore } from "../../lib/format";
import type { ConfluenceResult } from "../../types/api";
import { Card } from "../ui/Card";
import { DirectionBadge } from "../ui/DirectionBadge";

export function ConfluencePanel({ data, bare }: { data: ConfluenceResult | null; bare?: boolean }) {
  if (!data) {
    return <p className="text-sm text-zinc-500 p-4">No confluence data yet</p>;
  }

  const body = (
    <>
      <div className="flex items-end justify-between mb-4">
        <div>
          <p className="text-3xl font-mono font-bold text-amber-400">{formatScore(data.total_score)}</p>
          <p className="text-xs text-zinc-500 mt-1">{data.evidence_count} evidence sources</p>
        </div>
        <DirectionBadge direction={data.suggested_direction as "BUY" | "SELL" | "WAIT"} />
      </div>
      <p className="text-xs text-zinc-500 mb-3">
        Each row below is a reason the engine considered buying or selling.
      </p>
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {data.evidence.map((item) => (
          <div
            key={`${item.source}-${item.description}`}
            className="flex items-start gap-3 p-3 rounded-lg bg-zinc-800/50 border border-zinc-700/50"
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-medium text-zinc-200">{item.source}</span>
                <DirectionBadge direction={item.direction as "BUY" | "SELL" | "WAIT"} />
              </div>
              <p className="text-xs text-zinc-400 leading-relaxed">{item.description}</p>
            </div>
            <span className="text-xs font-mono text-amber-400 shrink-0">
              {formatScore(item.weighted_contribution)}
            </span>
          </div>
        ))}
        {data.evidence.length === 0 && (
          <p className="text-xs text-zinc-500">Not enough data for evidence yet</p>
        )}
      </div>
    </>
  );

  if (bare) return <div className="p-4">{body}</div>;

  return <Card title="Confluence">{body}</Card>;
}
