import { useState } from "react";
import { ConfluencePanel } from "../analysis/ConfluencePanel";
import { ContextPanel } from "../analysis/ContextPanel";
import { NewsPanel } from "../analysis/NewsPanel";
import { ValidationPanel } from "../analysis/ValidationPanel";
import type { ConfluenceResult, MarketContext, MTFAnalysis, NewsFilterStatus, ValidationResult } from "../../types/api";

const TABS = [
  { id: "evidence", label: "Evidence" },
  { id: "rules", label: "Rules" },
  { id: "market", label: "Market" },
] as const;

type TabId = (typeof TABS)[number]["id"];

interface AnalysisTabsProps {
  confluence: ConfluenceResult | null;
  validation: ValidationResult | null;
  context: MarketContext | null;
  mtf: MTFAnalysis | null;
  news: NewsFilterStatus | null;
}

export function AnalysisTabs({ confluence, validation, context, mtf, news }: AnalysisTabsProps) {
  const [tab, setTab] = useState<TabId>("evidence");

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/80 overflow-hidden">
      <div className="flex border-b border-zinc-800">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
              tab === t.id
                ? "text-amber-400 bg-zinc-800/80 border-b-2 border-amber-400"
                : "text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="p-1">
        {tab === "evidence" && <ConfluencePanel data={confluence} bare />}
        {tab === "rules" && <ValidationPanel data={validation} bare />}
        {tab === "market" && (
          <div className="space-y-4 p-4">
            <ContextPanel context={context} mtf={mtf} />
            <NewsPanel data={news} />
          </div>
        )}
      </div>
    </div>
  );
}
