import { AlertTriangle, Shield } from "lucide-react";
import { formatTime } from "../../lib/format";
import type { NewsFilterStatus } from "../../types/api";
import { Card } from "../ui/Card";

export function NewsPanel({ data }: { data: NewsFilterStatus | null }) {
  if (!data) {
    return (
      <Card title="News Filter">
        <p className="text-sm text-muted">No news data</p>
      </Card>
    );
  }

  return (
    <Card title="News Filter">
      <div className="flex items-center gap-3 mb-4">
        {data.is_blocked ? (
          <div className="flex items-center gap-2 text-sell">
            <AlertTriangle className="w-4 h-4" />
            <span className="text-sm font-semibold">Blocked</span>
          </div>
        ) : data.is_soft_downgrade ? (
          <div className="flex items-center gap-2 text-gold">
            <AlertTriangle className="w-4 h-4" />
            <span className="text-sm font-semibold">Soft downgrade active</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-buy">
            <Shield className="w-4 h-4" />
            <span className="text-sm font-semibold">Clear</span>
          </div>
        )}
      </div>

      {data.next_event && (
        <div className="p-3 rounded-lg bg-elevated/60 border border-border/40">
          <p className="text-[10px] font-mono uppercase tracking-wider text-muted mb-1">
            Next event
          </p>
          <p className="text-sm text-white/90">{data.next_event.name}</p>
          <p className="text-xs font-mono text-muted mt-1">
            {formatTime(data.next_event.scheduled_at)}
          </p>
        </div>
      )}
    </Card>
  );
}
