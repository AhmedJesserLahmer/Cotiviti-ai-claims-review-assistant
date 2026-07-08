"use client";

import { useState } from "react";
import { Sparkles, Loader2, RefreshCw, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";
import { AnalysisResult } from "@/lib/types";
import SignalsPanel from "./SignalsPanel";
import ReasoningNarrative from "./ReasoningNarrative";

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

  async function runAnalysis() {
    setLoading(true);
    setError(null);
    try {
      const result = await api.analyzeClaim(claimId);
      setAnalysis(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
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
        </>
      )}
    </div>
  );
}
