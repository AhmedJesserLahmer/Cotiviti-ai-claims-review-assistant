"use client";

import { useEffect, useRef, useState } from "react";
import { Sparkles, Loader2, RefreshCw, AlertTriangle, CheckCircle2 } from "lucide-react";
import { analysisStreamUrl, api } from "@/lib/api";
import { AnalysisResult } from "@/lib/types";
import SignalsPanel from "./SignalsPanel";
import ReasoningNarrative from "./ReasoningNarrative";
import AIReliabilityPanel from "./AIReliabilityPanel";
import ReviewerFeedback from "./ReviewerFeedback";

const STAGE_LABELS: Record<string, string> = {
  fetch_claim_context: "Loading claim, patient and provider history",
  run_ml_signals: "Scoring with ML models",
  reasoning_node: "Reasoning over the signals",
  recommendation_node: "Deciding and applying guardrails",
  persist_result: "Saving the audit trail",
};

export default function ClaimAnalysisSection({
  claimId,
  initialAnalysis,
}: {
  claimId: string;
  initialAnalysis: AnalysisResult | null;
}) {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(initialAnalysis);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stages, setStages] = useState<string[]>([]);
  const sourceRef = useRef<EventSource | null>(null);

  // Close any open stream when the component unmounts.
  useEffect(() => () => sourceRef.current?.close(), []);

  async function runWithoutStreaming(refresh: boolean) {
    try {
      setAnalysis(await api.analyzeClaim(claimId, refresh));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  function runAnalysis() {
    // A re-run must produce a fresh decision, not the cached one.
    const refresh = analysis !== null;
    setLoading(true);
    setError(null);
    setStages([]);

    if (typeof window === "undefined" || typeof EventSource === "undefined") {
      void runWithoutStreaming(refresh);
      return;
    }

    sourceRef.current?.close();
    const source = new EventSource(analysisStreamUrl(claimId, refresh));
    sourceRef.current = source;
    let finished = false;

    const finish = () => {
      finished = true;
      source.close();
      setLoading(false);
    };

    source.addEventListener("stage", (event) => {
      const { stage } = JSON.parse((event as MessageEvent).data) as { stage: string };
      setStages((previous) => (previous.includes(stage) ? previous : [...previous, stage]));
    });
    source.addEventListener("result", (event) => {
      setAnalysis(JSON.parse((event as MessageEvent).data) as AnalysisResult);
      finish();
    });
    source.addEventListener("error", (event) => {
      const data = (event as MessageEvent).data;
      if (typeof data === "string" && data.length > 0) {
        // Error event sent by the server: show it.
        const { detail } = JSON.parse(data) as { detail: string };
        setError(detail);
        finish();
      } else if (!finished) {
        // Transport failure (proxy, CORS, no SSE support): fall back to a plain request.
        source.close();
        void runWithoutStreaming(refresh);
      }
    });
  }

  return (
    <div className="space-y-4">
      <button
        onClick={runAnalysis}
        disabled={loading}
        className="btn-toon inline-flex items-center gap-2 bg-cotiviti-magenta px-5 py-2.5 font-display text-sm font-bold text-white disabled:opacity-60"
      >
        {loading ? (
          <>
            <Loader2 size={18} strokeWidth={3} className="animate-spin" />
            Running LangGraph agent…
          </>
        ) : analysis ? (
          <>
            <RefreshCw size={18} strokeWidth={3} />
            Re-run AI Analysis
          </>
        ) : (
          <>
            <Sparkles size={18} strokeWidth={3} />
            Run AI Analysis
          </>
        )}
      </button>

      {loading && stages.length > 0 && (
        <ol className="card-toon space-y-1 p-4 text-xs font-bold text-cotiviti-ink/80" aria-live="polite">
          {stages.map((stage) => (
            <li key={stage} className="flex items-center gap-2">
              <CheckCircle2 size={14} strokeWidth={3} className="text-cotiviti-teal" />
              {STAGE_LABELS[stage] ?? stage}
            </li>
          ))}
        </ol>
      )}

      {error && (
        <p className="flex items-center gap-2 rounded-xl border-[2.5px] border-cotiviti-ink bg-cotiviti-coral px-3 py-2 text-sm font-bold text-white">
          <AlertTriangle size={16} strokeWidth={3} />
          {error}
        </p>
      )}

      {analysis && (
        <>
          <SignalsPanel signals={analysis.signals} />
          <ReasoningNarrative analysis={analysis} />
          {analysis.ai_metadata && <AIReliabilityPanel meta={analysis.ai_metadata} />}
          <ReviewerFeedback key={analysis.ai_metadata?.run_id ?? "legacy"} claimId={claimId} analysis={analysis} />
        </>
      )}
    </div>
  );
}
