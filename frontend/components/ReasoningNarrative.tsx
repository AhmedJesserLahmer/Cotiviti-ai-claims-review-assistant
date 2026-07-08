import { BrainCircuit, CheckCircle2, Flag, HelpCircle, LucideIcon } from "lucide-react";
import { AnalysisResult } from "@/lib/types";

const RECOMMENDATION: Record<
  AnalysisResult["recommendation"],
  { classes: string; label: string; Icon: LucideIcon }
> = {
  approve: { classes: "bg-cotiviti-teal text-white", label: "Approve", Icon: CheckCircle2 },
  flag_for_review: { classes: "bg-cotiviti-gold text-cotiviti-ink", label: "Flag for Review", Icon: Flag },
  request_more_data: { classes: "bg-cotiviti-violet text-white", label: "Request More Data", Icon: HelpCircle },
};

export default function ReasoningNarrative({ analysis }: { analysis: AnalysisResult }) {
  const rec = RECOMMENDATION[analysis.recommendation];
  return (
    <div className="card-toon p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="flex items-center gap-2 font-display text-sm font-semibold uppercase tracking-wide text-cotiviti-purple">
          <BrainCircuit size={18} strokeWidth={2.5} className="text-cotiviti-magenta" />
          Agent Reasoning &amp; Recommendation
        </h3>
        <span className={`chip-toon inline-flex items-center gap-1.5 px-3 py-1 text-xs ${rec.classes}`}>
          <rec.Icon size={14} strokeWidth={3} />
          {rec.label}
        </span>
      </div>
      <p className="whitespace-pre-line text-sm font-semibold leading-relaxed text-cotiviti-ink/80">
        {analysis.reasoning}
      </p>
      <p className="mt-4 rounded-xl border-[2.5px] border-cotiviti-ink bg-cotiviti-lav px-3 py-2 text-sm font-extrabold text-cotiviti-ink">
        {analysis.recommendation_summary}
      </p>
      {analysis.loops > 0 && (
        <p className="mt-2 text-xs font-semibold text-cotiviti-ink/50">
          Agent requested additional data {analysis.loops} time(s) before deciding.
        </p>
      )}
    </div>
  );
}
