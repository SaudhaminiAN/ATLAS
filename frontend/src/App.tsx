import { DemoBanner } from "./components/layout/DemoBanner";
import { Header } from "./components/layout/Header";
import { SummaryCards } from "./components/layout/SummaryCards";
import { AnalysisTabs } from "./components/layout/AnalysisTabs";
import { ChartPanel } from "./components/chart/ChartPanel";
import { DecisionHistory } from "./components/decision/DecisionHistory";
import { ExplanationPanel } from "./components/decision/ExplanationPanel";
import { TradesPanel } from "./components/trades/TradesPanel";
import { AnalyticsPanel } from "./components/analytics/AnalyticsPanel";
import { useAnalysis } from "./hooks/useAnalysis";
import { useAnalytics } from "./hooks/useAnalytics";
import { useBars } from "./hooks/useBars";
import { useDecisionHistory } from "./hooks/useDecisionHistory";
import { useExplanation } from "./hooks/useExplanation";
import { useTrades } from "./hooks/useTrades";
import { useWebSocket } from "./hooks/useWebSocket";
import { SYMBOL } from "./lib/api";
import type { DecisionWsPayload } from "./types/api";
import { useCallback } from "react";

export default function App() {
  const { bars, loading: barsLoading, wsStatus: barWsStatus, reload } = useBars(SYMBOL);
  const analysis = useAnalysis(SYMBOL);
  const history = useDecisionHistory(SYMBOL);
  const analytics = useAnalytics(SYMBOL);
  const explanation = useExplanation(analysis.decision?.id);
  const trades = useTrades(SYMBOL);

  const onDecision = useCallback(() => {
    void analysis.refresh();
    void history.reload();
    void analytics.refresh();
    void explanation.reload();
    void trades.refresh();
    void reload();
  }, [analysis, history, analytics, explanation, trades, reload]);

  const { status: decisionWsStatus } = useWebSocket<DecisionWsPayload>({
    channel: `decisions.${SYMBOL}`,
    onMessage: onDecision,
  });

  const wsStatus =
    barWsStatus === "connected" || decisionWsStatus === "connected"
      ? "connected"
      : barWsStatus === "connecting" || decisionWsStatus === "connecting"
        ? "connecting"
        : barWsStatus === "error" || decisionWsStatus === "error"
          ? "error"
          : "disconnected";

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <DemoBanner />
      <Header
        wsStatus={wsStatus}
        session={analysis.context?.primary_session}
        newsBlocked={analysis.news?.is_blocked}
      />

      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 py-6 space-y-6">
        {analysis.error && (
          <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300 flex justify-between">
            <span>Could not load analysis: {analysis.error}</span>
            <button type="button" className="underline" onClick={() => void analysis.refresh()}>
              Retry
            </button>
          </div>
        )}

        <SummaryCards bars={bars} decision={analysis.decision} loading={analysis.loading} />

        <ExplanationPanel
          decisionId={analysis.decision?.id ?? null}
          explanation={explanation.explanation}
          loading={explanation.loading}
          generating={explanation.generating}
          error={explanation.error}
          onGenerate={() => void explanation.generate()}
        />

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2">
            <ChartPanel bars={bars} loading={barsLoading} />
          </div>
          <div>
            <AnalysisTabs
              confluence={analysis.confluence}
              validation={analysis.validation}
              context={analysis.context}
              mtf={analysis.mtf}
              news={analysis.news}
            />
          </div>
        </div>

        <DecisionHistory
          items={history.history?.items ?? []}
          loading={history.loading}
          total={history.history?.total ?? 0}
        />

        <TradesPanel
          trades={trades.trades}
          loading={trades.loading}
          error={trades.error}
          openCount={trades.openCount}
          closedPnl={trades.closedPnl}
          onRefresh={() => void trades.refresh()}
        />

        <AnalyticsPanel
          decisionStats={analytics.decisionStats}
          moduleAccuracy={analytics.moduleAccuracy}
          performance={analytics.performance}
          loading={analytics.loading}
          error={analytics.error}
          onRefresh={() => void analytics.refresh()}
        />
      </main>
    </div>
  );
}
