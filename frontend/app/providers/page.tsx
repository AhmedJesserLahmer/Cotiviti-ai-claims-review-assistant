import Link from "next/link";
import { ArrowLeft, Radar, Wallet } from "lucide-react";
import { api } from "@/lib/api";
import ProviderSparkline from "@/components/ProviderSparkline";

export default async function ProvidersIndexPage() {
  const providers = await api.listProviders();
  const timeseries = await Promise.all(
    providers.map((p) => api.getProviderTimeseries(p.provider_id).catch(() => []))
  );

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
        <h1 className="flex items-center gap-2 font-display text-2xl font-bold text-cotiviti-ink">
          <Radar size={24} strokeWidth={2.5} className="text-cotiviti-magenta" />
          Provider Billing Patterns
        </h1>
        <p className="mt-1 text-sm font-semibold text-cotiviti-ink/70">
          Every provider&apos;s daily billing time series, average billed amount, and behavior
          cluster in one place. Click a card for the full anomaly chart.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {providers.map((provider, i) => {
          const ts = timeseries[i];
          const anomalyCount = ts.filter((t) => t.is_anomaly).length;
          return (
            <Link
              key={provider.provider_id}
              href={`/providers/${provider.provider_id}`}
              className="card-toon block bg-white p-4 transition-transform hover:-translate-y-1"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate font-display text-sm font-bold text-cotiviti-ink">
                    {provider.name}
                  </p>
                  <p className="truncate text-xs font-semibold text-cotiviti-ink/60">
                    {provider.specialty} · {provider.provider_id}
                  </p>
                </div>
                <span className="chip-toon shrink-0 bg-cotiviti-violet px-2 py-0.5 text-[10px] text-white">
                  {provider.cluster_label}
                </span>
              </div>

              <div className="mt-3">
                <ProviderSparkline data={ts} />
              </div>

              <div className="mt-3 flex items-center justify-between text-xs font-bold text-cotiviti-ink/70">
                <span className="inline-flex items-center gap-1">
                  <Wallet size={13} strokeWidth={3} className="text-cotiviti-teal" />
                  Avg billed: ${provider.avg_billed.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </span>
                <span className={anomalyCount > 0 ? "text-cotiviti-coral" : "text-cotiviti-ink/40"}>
                  {anomalyCount} anomal{anomalyCount === 1 ? "y" : "ies"}
                </span>
              </div>
            </Link>
          );
        })}
      </div>
    </main>
  );
}
