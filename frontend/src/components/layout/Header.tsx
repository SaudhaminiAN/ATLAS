import { Activity, Radio } from "lucide-react";
import type { WsStatus } from "../../hooks/useWebSocket";

interface HeaderProps {
  wsStatus: WsStatus;
  session?: string;
  newsBlocked?: boolean;
}

export function Header({ wsStatus, session, newsBlocked }: HeaderProps) {
  const live = wsStatus === "connected";

  return (
    <header className="border-b border-zinc-800 bg-zinc-950/90 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xl font-bold tracking-tight text-white">ATLAS</span>
          <span className="hidden sm:inline text-sm text-zinc-500">Gold Analysis</span>
        </div>

        <div className="flex items-center gap-3 text-sm">
          {session && (
            <span className="hidden md:inline text-zinc-500 capitalize">
              {session.replace(/_/g, " ")} session
            </span>
          )}
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
              newsBlocked
                ? "bg-red-500/15 text-red-400"
                : "bg-emerald-500/15 text-emerald-400"
            }`}
          >
            <Activity className="w-3 h-3" />
            News {newsBlocked ? "blocked" : "ok"}
          </span>
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
              live ? "bg-emerald-500/15 text-emerald-400" : "bg-amber-500/15 text-amber-400"
            }`}
          >
            <Radio className={`w-3 h-3 ${live ? "" : "animate-pulse"}`} />
            {live ? "Live updates" : "Connecting…"}
          </span>
        </div>
      </div>
    </header>
  );
}
