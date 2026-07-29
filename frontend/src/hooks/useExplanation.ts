import { useCallback, useEffect, useState } from "react";
import { apiGetOptional, apiPost, endpoints } from "../lib/api";
import type { DecisionExplanation } from "../types/api";

interface UseExplanationState {
  explanation: DecisionExplanation | null;
  loading: boolean;
  generating: boolean;
  error: string | null;
  generate: () => Promise<void>;
  reload: () => Promise<void>;
}

export function useExplanation(decisionId: string | null | undefined): UseExplanationState {
  const [explanation, setExplanation] = useState<DecisionExplanation | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!decisionId) {
      setExplanation(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await apiGetOptional<DecisionExplanation>(endpoints.explanation(decisionId));
      setExplanation(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load explanation");
      setExplanation(null);
    } finally {
      setLoading(false);
    }
  }, [decisionId]);

  const generate = useCallback(async () => {
    if (!decisionId) return;
    setGenerating(true);
    setError(null);
    try {
      const data = await apiPost<DecisionExplanation>(endpoints.explanation(decisionId));
      setExplanation(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate explanation");
    } finally {
      setGenerating(false);
    }
  }, [decisionId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { explanation, loading, generating, error, generate, reload };
}
