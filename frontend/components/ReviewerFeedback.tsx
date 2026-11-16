"use client";

import { useState } from "react";
import { CheckCircle2, Flag, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { AnalysisResult, FinalDecision } from "@/lib/types";

const DECISIONS: { value: FinalDecision; label: string }[] = [
  { value: "approve", label: "Approve" },
  { value: "deny", label: "Deny" },
  { value: "flag_for_review", label: "Needs further review" },
  { value: "request_more_data", label: "Request more data" },
];

/**
 * Lets the reviewer confirm or override the AI decision. Every answer is stored
 * with a snapshot of the AI run and feeds the AI quality analytics.
 */
export default function ReviewerFeedback({ claimId, analysis }: { claimId: string; analysis: AnalysisResult }) {
  const [mode, setMode] = useState<"idle" | "override">("idle");
  const [decision, setDecision] = useState<FinalDecision>("deny");
  const [reviewer, setReviewer] = useState("");
  const [comment, setComment] = useState("");
  const [state, setState] = useState<"idle" | "saving" | "saved">("idle");
  const [error, setError] = useState<string | null>(null);

  async function send(verdict: "agree" | "override") {
    if (!reviewer.trim()) {
      setError("Enter your reviewer name first.");
      return;
    }
    setState("saving");
    setError(null);
    try {
      await api.submitFeedback(claimId, {
        verdict,
        final_decision: verdict === "agree" ? analysis.recommendation : decision,
        reviewer: reviewer.trim(),
        comment: comment.trim(),
      });
      setState("saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save feedback");
      setState("idle");
    }
  }

  if (state === "saved") {
    return (
      <p className="card-toon flex items-center gap-2 p-4 text-sm font-bold text-cotiviti-teal">
        <CheckCircle2 size={16} strokeWidth={3} /> Thanks, your review was recorded.
      </p>
    );
  }

  return (
    <div className="card-toon space-y-3 p-5">
      <h3 className="font-display text-sm font-semibold uppercase tracking-wide text-cotiviti-purple">
        Your review
      </h3>
      <input
        value={reviewer}
        onChange={(e) => setReviewer(e.target.value)}
        placeholder="Reviewer name"
        maxLength={80}
        aria-label="Reviewer name"
        className="w-full rounded-xl border-[2.5px] border-cotiviti-ink px-3 py-2 text-sm font-semibold"
      />
      {mode === "override" && (
        <div className="space-y-2">
          <select
            value={decision}
            onChange={(e) => setDecision(e.target.value as FinalDecision)}
            aria-label="Final decision"
            className="w-full rounded-xl border-[2.5px] border-cotiviti-ink px-3 py-2 text-sm font-semibold"
          >
            {DECISIONS.filter((d) => d.value !== analysis.recommendation).map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Why do you disagree? (optional)"
            maxLength={1000}
            rows={3}
            aria-label="Comment"
            className="w-full rounded-xl border-[2.5px] border-cotiviti-ink px-3 py-2 text-sm font-semibold"
          />
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {mode === "idle" ? (
          <>
            <button
              onClick={() => send("agree")}
              disabled={state === "saving"}
              className="btn-toon inline-flex items-center gap-1.5 bg-cotiviti-teal px-4 py-2 text-xs font-bold text-white disabled:opacity-60"
            >
              {state === "saving" ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} strokeWidth={3} />}
              Agree with AI
            </button>
            <button
              onClick={() => setMode("override")}
              className="btn-toon inline-flex items-center gap-1.5 bg-cotiviti-gold px-4 py-2 text-xs font-bold text-cotiviti-ink"
            >
              <Flag size={14} strokeWidth={3} />
              Override
            </button>
          </>
        ) : (
          <>
            <button
              onClick={() => send("override")}
              disabled={state === "saving"}
              className="btn-toon bg-cotiviti-magenta px-4 py-2 text-xs font-bold text-white disabled:opacity-60"
            >
              Submit override
            </button>
            <button onClick={() => setMode("idle")} className="px-3 py-2 text-xs font-bold text-cotiviti-ink/60">
              Cancel
            </button>
          </>
        )}
      </div>
      {error && <p className="text-xs font-bold text-cotiviti-coral">{error}</p>}
    </div>
  );
}
