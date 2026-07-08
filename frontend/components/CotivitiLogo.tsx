import { Activity } from "lucide-react";

export default function CotivitiLogo({ size = "md" }: { size?: "md" | "lg" }) {
  const text = size === "lg" ? "text-3xl" : "text-2xl";
  const box = size === "lg" ? "h-11 w-11" : "h-9 w-9";
  const icon = size === "lg" ? 26 : 22;

  return (
    <div className="flex items-center gap-2.5">
      <span
        className={`grid ${box} place-items-center rounded-2xl border-[3px] border-cotiviti-ink bg-cotiviti-magenta text-white shadow-[3px_3px_0_0_var(--color-cotiviti-ink)]`}
      >
        <Activity size={icon} strokeWidth={3} />
      </span>
      <span className={`font-display ${text} font-bold tracking-tight text-cotiviti-purple`}>
        cot<span className="text-cotiviti-magenta">i</span>v
        <span className="text-cotiviti-teal">i</span>ti
      </span>
    </div>
  );
}
