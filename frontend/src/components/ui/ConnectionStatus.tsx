import type { WsStatus } from "../../hooks/useWebSocket";

const labels: Record<WsStatus, string> = {
  connecting: "Connecting",
  connected: "Live",
  disconnected: "Reconnecting",
  error: "Offline",
};

const colors: Record<WsStatus, string> = {
  connecting: "bg-gold animate-pulse",
  connected: "bg-buy",
  disconnected: "bg-gold animate-pulse-slow",
  error: "bg-sell",
};

export function ConnectionStatus({ status }: { status: WsStatus }) {
  return (
    <div className="flex items-center gap-2 text-xs font-mono text-muted">
      <span className={`w-1.5 h-1.5 rounded-full ${colors[status]}`} />
      {labels[status]}
    </div>
  );
}
