import { formatPnl, formatPrice, formatTime, toNumber } from "../../lib/format";
import type { Trade } from "../../types/api";
import { DirectionBadge } from "../ui/DirectionBadge";
import { Card } from "../ui/Card";

interface TradesPanelProps {
  trades: Trade[];
  loading?: boolean;
  error?: string | null;
  openCount: number;
  closedPnl: number;
  onRefresh?: () => void;
}

const statusLabel: Record<string, string> = {
  open: "Open",
  partial: "Partial",
  closed: "Closed",
  rejected: "Rejected",
  cancelled: "Cancelled",
};

const statusStyle: Record<string, string> = {
  open: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  partial: "text-amber-400 bg-amber-500/10 border-amber-500/30",
  closed: "text-zinc-400 bg-zinc-800/60 border-zinc-700/40",
  rejected: "text-red-400 bg-red-500/10 border-red-500/30",
  cancelled: "text-zinc-500 bg-zinc-800/40 border-zinc-700/30",
};

export function TradesPanel({
  trades,
  loading,
  error,
  openCount,
  closedPnl,
  onRefresh,
}: TradesPanelProps) {
  const pnlColor =
    closedPnl > 0 ? "text-emerald-400" : closedPnl < 0 ? "text-red-400" : "text-zinc-400";

  return (
    <Card
      title="Paper trades"
      action={
        onRefresh ? (
          <button
            type="button"
            onClick={onRefresh}
            className="text-xs text-zinc-500 hover:text-amber-400 transition-colors"
          >
            Refresh
          </button>
        ) : null
      }
    >
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-5">
        <MiniStat label="Open positions" value={String(openCount)} />
        <MiniStat
          label="Closed P&L"
          value={formatPnl(closedPnl)}
          accent={pnlColor}
        />
        <MiniStat label="Total records" value={String(trades.length)} className="hidden sm:block" />
      </div>

      {error && (
        <p className="text-sm text-red-300 mb-4">{error}</p>
      )}

      {loading && trades.length === 0 ? (
        <div className="space-y-2">
          {[1, 2].map((i) => (
            <div key={i} className="skeleton h-14 w-full" />
          ))}
        </div>
      ) : trades.length === 0 ? (
        <div className="text-center py-8 space-y-2">
          <p className="text-sm text-zinc-400">No paper trades yet</p>
          <p className="text-xs text-zinc-500 max-w-md mx-auto">
            Trades appear when the engine issues a BUY or SELL and risk management is enabled
            (PIPELINE_RISK_ENABLED=true).
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto -mx-1">
          <table className="w-full text-left">
            <thead>
              <tr className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 border-b border-zinc-800">
                <th className="pb-3 pl-1 font-medium">Opened</th>
                <th className="pb-3 font-medium">Side</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Entry</th>
                <th className="pb-3 font-medium">Stop / Target</th>
                <th className="pb-3 font-medium">Size</th>
                <th className="pb-3 pr-1 font-medium">P&L</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade) => (
                <TradeRow key={trade.id} trade={trade} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function TradeRow({ trade }: { trade: Trade }) {
  const entry = trade.fill_price ?? trade.entry_price;
  const pnl =
    trade.status === "closed"
      ? trade.realized_pnl
      : trade.partial_realized_pnl && toNumber(trade.partial_realized_pnl) !== 0
        ? trade.partial_realized_pnl
        : null;
  const pnlNum = pnl !== null ? toNumber(pnl) : null;
  const pnlClass =
    pnlNum === null
      ? "text-zinc-500"
      : pnlNum >= 0
        ? "text-emerald-400"
        : "text-red-400";

  return (
    <tr className="border-b border-zinc-800/60 hover:bg-zinc-900/50 transition-colors">
      <td className="py-3 pl-1 text-xs font-mono text-zinc-500 whitespace-nowrap">
        {formatTime(trade.opened_at)}
      </td>
      <td className="py-3">
        <DirectionBadge direction={trade.direction} />
      </td>
      <td className="py-3">
        <span
          className={`inline-block text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${statusStyle[trade.status] ?? statusStyle.closed}`}
        >
          {statusLabel[trade.status] ?? trade.status}
        </span>
      </td>
      <td className="py-3 text-xs font-mono text-zinc-200">{formatPrice(entry)}</td>
      <td className="py-3 text-xs font-mono text-zinc-400">
        {formatPrice(trade.stop_loss)} / {formatPrice(trade.take_profit)}
      </td>
      <td className="py-3 text-xs font-mono text-zinc-400">
        {trade.remaining_size != null && trade.status !== "closed"
          ? `${toNumber(trade.remaining_size).toFixed(2)} lot`
          : `${toNumber(trade.position_size).toFixed(2)} lot`}
      </td>
      <td className={`py-3 pr-1 text-xs font-mono font-semibold ${pnlClass}`}>
        {formatPnl(pnl)}
      </td>
    </tr>
  );
}

function MiniStat({
  label,
  value,
  accent = "text-zinc-100",
  className = "",
}: {
  label: string;
  value: string;
  accent?: string;
  className?: string;
}) {
  return (
    <div className={`rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 py-2.5 ${className}`}>
      <p className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">{label}</p>
      <p className={`text-lg font-mono font-semibold ${accent}`}>{value}</p>
    </div>
  );
}
