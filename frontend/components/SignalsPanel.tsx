import { Tags, TrendingUp, Users, Radar, LucideIcon } from "lucide-react";
import { MLSignals } from "@/lib/types";
import RiskBadge from "./RiskBadge";

export default function SignalsPanel({ signals }: { signals: MLSignals }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Card title="Classification" Icon={Tags} color="bg-cotiviti-violet">
        <RiskBadge label={signals.predicted_risk_label} />
        <p className="mt-2 text-xs font-semibold text-cotiviti-ink/60">
          {Object.entries(signals.risk_probabilities)
            .map(([k, v]) => `${k}: ${(v * 100).toFixed(0)}%`)
            .join(" · ")}
        </p>
      </Card>
      <Card title="Prediction" Icon={TrendingUp} color="bg-cotiviti-teal">
        <p className="font-display text-2xl font-bold text-cotiviti-ink">
          ${signals.predicted_paid_amount.toLocaleString()}
        </p>
        <p className="mt-1 text-xs font-semibold text-cotiviti-ink/60">predicted paid amount</p>
      </Card>
      <Card title="Clustering" Icon={Users} color="bg-cotiviti-gold">
        <p className="text-sm font-extrabold text-cotiviti-ink">{signals.provider_cluster_label}</p>
        <p className="mt-1 text-xs font-semibold text-cotiviti-ink/60">
          cluster #{signals.provider_cluster_id}
        </p>
      </Card>
      <Card title="Anomaly Detection" Icon={Radar} color="bg-cotiviti-magenta">
        <p
          className={`text-sm font-extrabold ${
            signals.is_recent_anomaly ? "text-cotiviti-coral" : "text-cotiviti-teal"
          }`}
        >
          {signals.is_recent_anomaly ? "Anomalous billing!" : "Normal pattern"}
        </p>
        <p className="mt-1 text-xs font-semibold text-cotiviti-ink/60">
          {signals.anomaly_flagged_days} anomalous day(s) in window
        </p>
      </Card>
    </div>
  );
}

function Card({
  title,
  Icon,
  color,
  children,
}: {
  title: string;
  Icon: LucideIcon;
  color: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card-toon p-4">
      <div className="mb-2 flex items-center gap-2">
        <span
          className={`grid h-7 w-7 place-items-center rounded-lg border-[2.5px] border-cotiviti-ink text-white ${color}`}
        >
          <Icon size={15} strokeWidth={3} />
        </span>
        <h3 className="font-display text-xs font-semibold uppercase tracking-wide text-cotiviti-purple">
          {title}
        </h3>
      </div>
      {children}
    </div>
  );
}
