import { ShieldCheck, ShieldAlert, ShieldX } from "lucide-react";

const CONFIG: Record<string, { classes: string; Icon: typeof ShieldCheck }> = {
  Low: { classes: "bg-cotiviti-teal text-white", Icon: ShieldCheck },
  Medium: { classes: "bg-cotiviti-gold text-cotiviti-ink", Icon: ShieldAlert },
  High: { classes: "bg-cotiviti-coral text-white", Icon: ShieldX },
};

export default function RiskBadge({ label }: { label: string }) {
  const { classes, Icon } = CONFIG[label] ?? {
    classes: "bg-cotiviti-lav text-cotiviti-ink",
    Icon: ShieldAlert,
  };
  return (
    <span className={`chip-toon inline-flex items-center gap-1.5 px-3 py-1 text-xs ${classes}`}>
      <Icon size={14} strokeWidth={3} />
      {label}
    </span>
  );
}
