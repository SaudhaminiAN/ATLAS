import { BarChart3, RefreshCw } from "lucide-react";
import { formatScore, toNumber } from "../../lib/format";
import type { DecisionStats, ModuleAccuracy, PerformanceSummary } from "../../types/api";

interface AnalyticsPanelProps {
  decisionStats: DecisionStats | null;
  moduleAccuracy: ModuleAccuracy[];
  performance: PerformanceSummary | null;
  loading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
}

function formatRate(value: string | number): string {
  return `${(toNumber(value) * 100).toFixed(0)}%`;
}

function formatSource(source: string): string {
  return source.replace(/_/g, " ");
}

export function AnalyticsPanel({
  decisionStats,
  moduleAccuracy,
  performance,
  loading,
  error,
  onRefresh,
}: AnalyticsPanelProps) {
  return (
    <section className="rounded-xl border border-zinc-800 bg-zinc-900/80 overflow-hidden">
      <div className="px-5 py-4 border-b border-zinc-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-amber-400" />
          <div>
            <h2 className="text-lg font-semibold text-white">Analytics</h2>
            <p className="text-sm text-zinc-500">How often the engine waits vs trades</p>
          </div>
        </div>
        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            className="text-xs text-zinc-400 hover:text-zinc-200 flex items-center gap-1"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
        )}
      </div>

      <div className="p-5 space-y-6">
        {error && (
          <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300 flex justify-between">
            <span>{error}</span>
            {onRefresh && (
              <button type="button" className="underline" onClick={onRefresh}>
                Retry
              </button>
            )}
          </div>
        )}

        {loading && !decisionStats ? (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="skeleton h-20 rounded-xl" />
            ))}
          </div>
        ) : decisionStats ? (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <StatCard label="Total decisions" value={String(decisionStats.total_decisions)} />
              <StatCard
                label="WAIT rate"
                value={formatRate(decisionStats.wait_rate)}
                sub={`${decisionStats.wait_count} waits`}
                accent="text-zinc-300"
              />
              <StatCard
                label="Trade signals"
                value={formatRate(decisionStats.actionable_rate)}
                sub={`${decisionStats.actionable_count} BUY/SELL`}
                accent="text-emerald-400"
              />
              <StatCard
                label="BUY / SELL"
                value={`${decisionStats.buy_count} / ${decisionStats.sell_count}`}
                sub="Actionable only"
              />
            </div>

            {decisionStats.top_wait_reasons.length > 0 && (
              <div>
                <h3 className="text-xs uppercase tracking-wider text-zinc-500 mb-3">
                  Top reasons for WAIT
                </h3>
                <div className="space-y-2">
                  {decisionStats.top_wait_reasons.map((item) => (
                    <div
                      key={item.reason}
                      className="flex items-center justify-between gap-4 py-2 px-3 rounded-lg bg-zinc-800/50 border border-zinc-700/50"
                    >
                      <span className="text-sm text-zinc-300 flex-1">{item.reason}</span>
                      <span className="text-xs font-mono text-amber-400 shrink-0">
                        {item.count}×
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {moduleAccuracy.length > 0 && (
              <div>
                <h3 className="text-xs uppercase tracking-wider text-zinc-500 mb-3">
                  Evidence sources
                </h3>
                <p className="text-xs text-zinc-600 mb-3">
                  How often each analysis module contributed evidence (score ≥ 30%).
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="text-[10px] uppercase tracking-wider text-zinc-500 border-b border-zinc-800">
                        <th className="pb-2 font-medium">Source</th>
                        <th className="pb-2 font-medium">Appearances</th>
                        <th className="pb-2 font-medium">On WAIT</th>
                        <th className="pb-2 font-medium">Win rate</th>
                      </tr>
                    </thead>
                    <tbody>
                      {moduleAccuracy.map((row) => (
                        <tr
                          key={row.source}
                          className="border-b border-zinc-800/60 text-zinc-300"
                        >
                          <td className="py-2.5 capitalize">{formatSource(row.source)}</td>
                          <td className="py-2.5 font-mono">{row.appearances}</td>
                          <td className="py-2.5 font-mono text-zinc-500">{row.neutral_wait}</td>
                          <td className="py-2.5 font-mono text-zinc-500">
                            {row.true_positive > 0
                              ? formatScore(row.true_positive_rate)
                              : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <PerformanceSection performance={performance} />
          </>
        ) : (
          <p className="text-sm text-zinc-500 text-center py-8">
            No analytics data yet — decisions will appear here as the engine runs.
          </p>
        )}
      </div>
    </section>
  );
}

function StatCard({
  label,
  value,
  sub,
  accent = "text-white",
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
      <p className="text-[11px] uppercase tracking-wider text-zinc-500 mb-2">{label}</p>
      <p className={`font-mono font-bold text-2xl ${accent}`}>{value}</p>
      {sub && <p className="text-xs text-zinc-500 mt-1">{sub}</p>}
    </div>
  );
}

function PerformanceSection({ performance }: { performance: PerformanceSummary | null }) {
  const hasTrades = performance && performance.total_trades > 0;

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950/30 p-4">
      <h3 className="text-xs uppercase tracking-wider text-zinc-500 mb-2">
        Trade performance
      </h3>
      {hasTrades ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-zinc-500 block text-xs">Win rate</span>
            <span className="font-mono text-emerald-400">
              {formatScore(performance.win_rate)}
            </span>
          </div>
          <div>
            <span className="text-zinc-500 block text-xs">Profit factor</span>
            <span className="font-mono">{toNumber(performance.profit_factor).toFixed(2)}</span>
          </div>
          <div>
            <span className="text-zinc-500 block text-xs">Total P&amp;L</span>
            <span className="font-mono">{toNumber(performance.total_pnl).toFixed(2)}</span>
          </div>
          <div>
            <span className="text-zinc-500 block text-xs">Max drawdown</span>
            <span className="font-mono text-red-400">
              {formatScore(performance.max_drawdown)}
            </span>
          </div>
        </div>
      ) : (
        <p className="text-sm text-zinc-500">
          Paper trading not started yet — win rate and profit factor will appear after Spec 11
          (execution engine).
        </p>
      )}
    </div>
  );
}
