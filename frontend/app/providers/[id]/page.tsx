import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, Users, Wallet, FileStack, XCircle, Radar } from "lucide-react";
import { api } from "@/lib/api";
import AnomalyChart from "@/components/AnomalyChart";

export default async function ProviderDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  const providers = await api.listProviders();
  const provider = providers.find((p) => p.provider_id === id);
  if (!provider) notFound();

  const timeseries = await api.getProviderTimeseries(id).catch(() => []);
  const anomalyCount = timeseries.filter((t) => t.is_anomaly).length;

  const stats = [
    { label: "Cluster", value: provider.cluster_label, Icon: Users, color: "bg-cotiviti-violet" },
    { label: "Avg Billed", value: `$${provider.avg_billed.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, Icon: Wallet, color: "bg-cotiviti-teal" },
    { label: "Claim Volume", value: `${provider.claim_volume}`, Icon: FileStack, color: "bg-cotiviti-gold" },
    { label: "Denial Rate", value: `${(provider.denial_rate * 100).toFixed(1)}%`, Icon: XCircle, color: "bg-cotiviti-magenta" },
  ];

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 font-extrabold text-cotiviti-purple hover:underline"
      >
        <ArrowLeft size={16} strokeWidth={3} />
        Back to claims
      </Link>

      <header className="card-toon mt-4 mb-6 bg-cotiviti-cream p-5">
        <h1 className="font-display text-2xl font-bold text-cotiviti-ink">{provider.name}</h1>
        <p className="mt-1 text-sm font-semibold text-cotiviti-ink/70">
          {provider.specialty} · {provider.region} · {provider.provider_id}
        </p>
      </header>

      <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {stats.map(({ label, value, Icon, color }) => (
          <div key={label} className="card-toon p-4">
            <span className={`grid h-7 w-7 place-items-center rounded-lg border-[2.5px] border-cotiviti-ink text-white ${color}`}>
              <Icon size={15} strokeWidth={3} />
            </span>
            <dt className="mt-2 text-xs font-bold uppercase text-cotiviti-ink/50">{label}</dt>
            <dd className="font-display text-base font-bold text-cotiviti-ink">{value}</dd>
          </div>
        ))}
      </div>

      <h2 className="mb-2 flex items-center gap-2 font-display text-lg font-bold text-cotiviti-ink">
        <Radar size={20} strokeWidth={2.5} className="text-cotiviti-magenta" />
        Billing Time Series
        <span className="chip-toon bg-cotiviti-coral px-2.5 py-0.5 text-xs text-white">
          {anomalyCount} anomalous day(s)
        </span>
      </h2>
      <AnomalyChart data={timeseries} />
    </main>
  );
}
