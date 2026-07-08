"use client";

import Link from "next/link";
import { FileText, Building2, ArrowRight } from "lucide-react";
import { Claim } from "@/lib/types";
import RiskBadge from "./RiskBadge";

export default function ClaimTable({ claims }: { claims: Claim[] }) {
  return (
    <div className="card-toon overflow-x-auto p-2">
      <table className="min-w-full border-separate border-spacing-y-1 text-sm">
        <thead>
          <tr className="text-left font-display text-xs uppercase tracking-wide text-cotiviti-purple">
            <th className="px-4 py-2">Claim</th>
            <th className="px-4 py-2">Provider</th>
            <th className="px-4 py-2">Treatment</th>
            <th className="px-4 py-2">Billed</th>
            <th className="px-4 py-2">Status</th>
            <th className="px-4 py-2">Risk</th>
            <th className="px-4 py-2"></th>
          </tr>
        </thead>
        <tbody>
          {claims.map((claim) => (
            <tr
              key={claim.claim_id}
              className="rounded-xl bg-cotiviti-cream/60 transition-colors hover:bg-cotiviti-lav"
            >
              <td className="rounded-l-xl px-4 py-2.5">
                <Link
                  href={`/claims/${claim.claim_id}`}
                  className="inline-flex items-center gap-1.5 font-extrabold text-cotiviti-purple hover:underline"
                >
                  <FileText size={15} strokeWidth={3} />
                  {claim.claim_id}
                </Link>
              </td>
              <td className="px-4 py-2.5">
                <Link
                  href={`/providers/${claim.provider_id}`}
                  className="inline-flex items-center gap-1.5 font-semibold text-cotiviti-ink hover:underline"
                >
                  <Building2 size={15} strokeWidth={2.5} />
                  {claim.provider_id}
                </Link>
              </td>
              <td className="px-4 py-2.5 font-semibold text-cotiviti-ink">{claim.treatment_type}</td>
              <td className="px-4 py-2.5 font-extrabold text-cotiviti-ink">
                ${claim.billed_amount.toLocaleString()}
              </td>
              <td className="px-4 py-2.5 font-semibold text-cotiviti-ink/80">{claim.status}</td>
              <td className="px-4 py-2.5">
                <RiskBadge label={claim.risk_label} />
              </td>
              <td className="rounded-r-xl px-4 py-2.5">
                <Link href={`/claims/${claim.claim_id}`} className="text-cotiviti-magenta">
                  <ArrowRight size={18} strokeWidth={3} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
