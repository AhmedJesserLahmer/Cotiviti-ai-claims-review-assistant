import Link from "next/link";
import { Sparkles, LineChart, Layers } from "lucide-react";
import { api } from "@/lib/api";
import ClaimTable from "@/components/ClaimTable";
import AppMockup from "@/components/AppMockup";
import UploadClaimsButton from "@/components/UploadClaimsButton";

export default async function DashboardPage() {
  const claims = await api.listClaims();

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <section className="card-toon mb-8 flex flex-col items-center gap-6 bg-cotiviti-purple p-6 text-white lg:flex-row lg:justify-between">
        <div>
          <h1 className="flex items-center gap-2 font-display text-3xl font-bold">
            <Sparkles size={30} strokeWidth={2.5} className="text-cotiviti-gold" />
            AI Claims Review Assistant
          </h1>
          <p className="mt-2 max-w-2xl font-semibold text-white/90">
            A Cotiviti clinical decision-making POC — classification, prediction, clustering,
            anomaly detection, and a LangGraph reasoning agent working together over synthetic
            healthcare claims.
          </p>
          <div className="mt-4 flex flex-wrap gap-2 text-sm font-extrabold text-cotiviti-ink">
            <span className="chip-toon bg-cotiviti-gold px-3 py-1">{claims.length} claims loaded</span>
            <span className="chip-toon inline-flex items-center gap-1.5 bg-cotiviti-teal px-3 py-1 text-white">
              <Layers size={14} strokeWidth={3} /> 6 AI capabilities
            </span>
          </div>
        </div>
        <AppMockup />
      </section>

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-xl font-bold text-cotiviti-ink">Claims Queue</h2>
        <div className="flex flex-wrap items-center gap-2">
          <UploadClaimsButton />
          <Link
            href="/providers"
            className="btn-toon inline-flex items-center gap-1.5 bg-cotiviti-violet px-4 py-2 text-sm font-bold text-white"
          >
            <LineChart size={16} strokeWidth={3} />
            View all provider patterns
          </Link>
        </div>
      </div>

      <ClaimTable claims={claims} />
    </main>
  );
}
