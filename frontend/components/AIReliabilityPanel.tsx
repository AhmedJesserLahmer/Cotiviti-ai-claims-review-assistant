import { AlertTriangle, ShieldAlert, ShieldCheck, ShieldX } from "lucide-react";
import { AIMetadata } from "@/lib/types";

/**
 * Shows how an AI decision was produced: which model answered, whether the
 * system fell back to another model or to the rule engine, which guardrails
 * fired, and whether policy overrode the model. Reviewers need this to judge
 * how much weight to give the recommendation.
 */
export default function AIReliabilityPanel({ meta }: { meta: AIMetadata }) {
  const status = meta.degraded
    ? {
        label: "Rule engine (AI unavailable)",
        classes: "bg-cotiviti-gold text-cotiviti-ink",
        Icon: ShieldAlert,
      }
    : meta.recommendation_overridden
      ? {
          label: "Escalated by policy guardrail",
          classes: "bg-cotiviti-coral text-white",
          Icon: ShieldX,
        }
      : {
          label: "AI decision passed all guardrails",
          classes: "bg-cotiviti-teal text-white",
          Icon: ShieldCheck,
        };

  const failedAttempts = meta.attempts.filter((a) => a.outcome !== "success").length;
  const firedGuardrails = meta.guardrail_events.filter((e) => e.guardrail !== "policy");

  return (
    <div className="card-toon p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-display text-sm font-semibold uppercase tracking-wide text-cotiviti-purple">
          AI Reliability
        </h3>
        <span className={`chip-toon inline-flex items-center gap-1.5 px-3 py-1 text-xs ${status.classes}`}>
          <status.Icon size={14} strokeWidth={3} />
          {status.label}
        </span>
      </div>

      <dl className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
        <Stat label="Decision source" value={meta.decision_source === "llm" ? "LLM" : "Rules"} />
        <Stat
          label="Model"
          value={meta.model_used ? `${meta.model_used}${meta.model_fallback_used ? " (fallback)" : ""}` : "none"}
        />
        <Stat
          label="Confidence"
          value={meta.confidence == null ? "n/a" : `${Math.round(meta.confidence * 100)}%`}
        />
        <Stat
          label="Latency"
          value={meta.total_latency_ms == null ? "n/a" : `${(meta.total_latency_ms / 1000).toFixed(1)}s`}
        />
        <Stat label="Attempts" value={`${meta.attempts.length} (${failedAttempts} failed)`} />
        <Stat label="JSON repairs" value={String(meta.repair_attempts)} />
        <Stat label="Guardrail events" value={String(firedGuardrails.length)} />
        <Stat
          label="Prompts"
          value={Object.entries(meta.prompt_versions)
            .map(([name, version]) => `${name.replace("claim_", "")}@${version}`)
            .join(", ") || "n/a"}
        />
      </dl>

      {meta.recommendation_overridden && meta.original_recommendation && (
        <p className="mt-3 text-xs font-bold text-cotiviti-ink/70">
          The model proposed <code>{meta.original_recommendation}</code>; policy escalated it to manual review.
        </p>
      )}

      {meta.degraded && meta.degraded_reason && (
        <p className="mt-3 text-xs font-bold text-cotiviti-ink/70">Reason: {meta.degraded_reason}</p>
      )}

      {meta.injection_detected && (
        <p className="mt-3 flex items-center gap-2 rounded-xl border-[2.5px] border-cotiviti-ink bg-cotiviti-coral px-3 py-2 text-xs font-bold text-white">
          <AlertTriangle size={14} strokeWidth={3} />
          Suspicious text was removed from this claim&apos;s fields before AI analysis.
        </p>
      )}

      {meta.key_factors.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {meta.key_factors.map((factor) => (
            <span key={factor} className="chip-toon bg-cotiviti-lav px-2 py-0.5 text-[11px] text-cotiviti-ink">
              {factor}
            </span>
          ))}
        </div>
      )}

      {meta.guardrail_events.length > 0 && (
        <details className="mt-3 text-xs">
          <summary className="cursor-pointer font-bold text-cotiviti-purple">Guardrail log</summary>
          <ul className="mt-2 space-y-1 font-semibold text-cotiviti-ink/70">
            {meta.guardrail_events.map((event, index) => (
              <li key={`${event.guardrail}-${index}`}>
                <span className="font-extrabold">{event.guardrail}</span> · {event.action} · {event.detail}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="font-bold uppercase tracking-wide text-cotiviti-ink/50">{label}</dt>
      <dd className="break-words font-extrabold text-cotiviti-ink">{value}</dd>
    </div>
  );
}
