import { Sparkles } from "lucide-react";
import { Card } from "../ui/Card";
import type { DecisionExplanation } from "../../types/api";
import { formatTime } from "../../lib/format";

interface ExplanationPanelProps {
  explanation: DecisionExplanation | null;
  loading?: boolean;
  generating?: boolean;
  error?: string | null;
  onGenerate: () => void;
  decisionId: string | null;
}

export function ExplanationPanel({
  explanation,
  loading,
  generating,
  error,
  onGenerate,
  decisionId,
}: ExplanationPanelProps) {
  const busy = loading || generating;

  return (
    <Card
      title="AI explanation"
      action={
        decisionId && !busy ? (
          <button
            type="button"
            onClick={onGenerate}
            className="inline-flex items-center gap-1.5 text-xs text-amber-400 hover:text-amber-300 transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5" />
            {explanation ? "Refresh" : "Explain"}
          </button>
        ) : null
      }
    >
      {!decisionId ? (
        <p className="text-sm text-zinc-500">Waiting for a decision to explain…</p>
      ) : busy && !explanation ? (
        <div className="space-y-2">
          <div className="skeleton h-4 w-full" />
          <div className="skeleton h-4 w-5/6" />
          <div className="skeleton h-4 w-4/6" />
        </div>
      ) : error ? (
        <div className="space-y-3">
          <p className="text-sm text-red-300">{error}</p>
          <button
            type="button"
            onClick={onGenerate}
            className="text-sm text-amber-400 hover:underline"
          >
            Try again
          </button>
        </div>
      ) : explanation ? (
        <div className="space-y-3">
          <p className="text-sm text-zinc-200 leading-relaxed">{explanation.content}</p>
          <p className="text-[11px] text-zinc-500 font-mono">
            {formatTime(explanation.created_at)} · {explanation.provider}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-zinc-400">
            Get a plain-English summary of why ATLAS chose this signal — based only on the
            stored analysis snapshot.
          </p>
          <button
            type="button"
            onClick={onGenerate}
            className="inline-flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-sm text-amber-300 hover:bg-amber-500/20 transition-colors"
          >
            <Sparkles className="w-4 h-4" />
            Explain this decision
          </button>
        </div>
      )}
    </Card>
  );
}
