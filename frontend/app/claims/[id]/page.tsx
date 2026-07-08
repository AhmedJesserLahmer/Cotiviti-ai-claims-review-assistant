import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, DollarSign, BadgeDollarSign, BedDouble, ClipboardCheck } from "lucide-react";
import { api } from "@/lib/api";
import RiskBadge from "@/components/RiskBadge";
import ClaimAnalysisSection from "@/components/ClaimAnalysisSection";

export default async function ClaimDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  const claim = await api.getClaim(id).catch(() => null);
  if (!claim) notFound();

  const analysis = await api.getAnalysis(id).catch(() => null);

  const stats = [
    { label: "Billed", value: `$${claim.billed_amount.toLocaleString()}`, Icon: DollarSign, color: "bg-cotiviti-violet" },
    { label: "Paid", value: `$${claim.paid_amount.toLocaleString()}`, Icon: BadgeDollarSign, color: "bg-cotiviti-teal" },
    { label: "Length of Stay", value: `${claim.length_of_stay} day(s)`, Icon: BedDouble, color: "bg-cotiviti-gold" },
    { label: "Status", value: claim.status, Icon: ClipboardCheck, color: "bg-cotiviti-magenta" },
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

      <header className="card-toon mt-4 mb-6 flex items-start justify-between bg-cotiviti-cream p-5">
        <div>
          <h1 className="font-display text-2xl font-bold text-cotiviti-ink">{claim.claim_id}</h1>
          <p className="mt-1 text-sm font-semibold text-cotiviti-ink/70">
            {claim.treatment_type} · {claim.procedure_code} · {claim.diagnosis_code} ·{" "}
            <Link href={`/providers/${claim.provider_id}`} className="text-cotiviti-magenta hover:underline">
              {claim.provider_id}
            </Link>
          </p>
        </div>
        <RiskBadge label={claim.risk_label} />
      </header>

      <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {stats.map(({ label, value, Icon, color }) => (
          <div key={label} className="card-toon p-4">
            <span className={`grid h-7 w-7 place-items-center rounded-lg border-[2.5px] border-cotiviti-ink text-white ${color}`}>
              <Icon size={15} strokeWidth={3} />
            </span>
            <dt className="mt-2 text-xs font-bold uppercase text-cotiviti-ink/50">{label}</dt>
            <dd className="font-display text-lg font-bold text-cotiviti-ink">{value}</dd>
          </div>
        ))}
      </div>

      <ClaimAnalysisSection claimId={claim.claim_id} initialAnalysis={analysis} />
    </main>
  );
}
