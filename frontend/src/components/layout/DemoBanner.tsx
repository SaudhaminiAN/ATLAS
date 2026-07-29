import { AlertCircle } from "lucide-react";

export function DemoBanner() {
  return (
    <div className="bg-amber-500/10 border-b border-amber-500/30 px-4 py-2.5">
      <div className="max-w-[1600px] mx-auto flex items-start gap-3">
        <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-sm">
          <span className="font-semibold text-amber-300">Demo mode — not live gold prices.</span>
          <span className="text-amber-200/70 ml-2">
            ATLAS uses simulated M15 bars to test the analysis engine. Connect a real broker feed
            in a later phase for live trading data.
          </span>
        </div>
      </div>
    </div>
  );
}
