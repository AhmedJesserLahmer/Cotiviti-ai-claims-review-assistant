"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  UploadCloud,
  FileSpreadsheet,
  X,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Download,
  Sparkles,
} from "lucide-react";
import { api } from "@/lib/api";
import { ClaimUploadResponse } from "@/lib/types";

const TEMPLATE_CSV =
  "provider_id,procedure_code,diagnosis_code,treatment_type,billed_amount,age,patient_id,paid_amount,length_of_stay,prior_claims_count,status,claim_date,claim_id\n" +
  "PRV0000,CPT10005,ICD210,Outpatient,1200.50,45,,,,,,,\n";

function downloadTemplate() {
  const blob = new Blob([TEMPLATE_CSV], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "claims_upload_template.csv";
  a.click();
  URL.revokeObjectURL(url);
}

export default function UploadClaimsModal({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [autoAnalyze, setAutoAnalyze] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ClaimUploadResponse | null>(null);

  function pickFile(f: File | undefined | null) {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".csv")) {
      setError("Please choose a .csv file");
      return;
    }
    setError(null);
    setFile(f);
  }

  async function submit() {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.uploadClaims(file, autoAnalyze);
      setResult(res);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-cotiviti-ink/50 p-4">
      <div className="card-toon max-h-[90vh] w-full max-w-lg overflow-y-auto bg-white p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="flex items-center gap-2 font-display text-xl font-bold text-cotiviti-ink">
            <UploadCloud size={22} strokeWidth={2.5} className="text-cotiviti-magenta" />
            Upload Claims
          </h2>
          <button
            onClick={onClose}
            className="btn-toon grid h-8 w-8 place-items-center bg-cotiviti-lav text-cotiviti-ink"
            aria-label="Close"
          >
            <X size={16} strokeWidth={3} />
          </button>
        </div>

        {!result && (
          <>
            <p className="mb-3 text-sm font-semibold text-cotiviti-ink/70">
              Upload one or many claims at once via CSV. Each row needs a valid{" "}
              <Link href="/providers" className="text-cotiviti-magenta hover:underline">
                provider_id
              </Link>
              , procedure/diagnosis codes, treatment type, billed amount, and patient age.
            </p>

            <button
              onClick={downloadTemplate}
              className="btn-toon mb-4 inline-flex items-center gap-1.5 bg-cotiviti-gold px-3 py-1.5 text-xs font-bold text-cotiviti-ink"
            >
              <Download size={14} strokeWidth={3} />
              Download CSV template
            </button>

            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                pickFile(e.dataTransfer.files?.[0]);
              }}
              onClick={() => inputRef.current?.click()}
              className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-[3px] border-dashed p-8 text-center transition-colors ${
                dragging
                  ? "border-cotiviti-magenta bg-cotiviti-lav"
                  : "border-cotiviti-ink/40 bg-cotiviti-cream"
              }`}
            >
              <FileSpreadsheet size={32} strokeWidth={2} className="text-cotiviti-purple" />
              {file ? (
                <p className="text-sm font-extrabold text-cotiviti-ink">{file.name}</p>
              ) : (
                <p className="text-sm font-bold text-cotiviti-ink/60">
                  Drag &amp; drop a .csv, or click to browse
                </p>
              )}
              <input
                ref={inputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={(e) => pickFile(e.target.files?.[0])}
              />
            </div>

            <label className="mt-4 flex items-center gap-2 text-sm font-bold text-cotiviti-ink">
              <input
                type="checkbox"
                checked={autoAnalyze}
                onChange={(e) => setAutoAnalyze(e.target.checked)}
                className="h-4 w-4 accent-cotiviti-magenta"
              />
              <Sparkles size={15} strokeWidth={3} className="text-cotiviti-magenta" />
              Run AI Analysis on every uploaded claim immediately
            </label>

            {error && (
              <p className="mt-3 flex items-center gap-2 rounded-xl border-[2.5px] border-cotiviti-ink bg-cotiviti-coral px-3 py-2 text-sm font-bold text-white">
                <AlertTriangle size={16} strokeWidth={3} />
                {error}
              </p>
            )}

            <button
              onClick={submit}
              disabled={!file || loading}
              className="btn-toon mt-4 flex w-full items-center justify-center gap-2 bg-cotiviti-magenta px-5 py-2.5 font-display text-sm font-bold text-white disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 size={18} strokeWidth={3} className="animate-spin" />
                  Uploading{autoAnalyze ? " & analyzing…" : "…"}
                </>
              ) : (
                <>
                  <UploadCloud size={18} strokeWidth={3} />
                  Upload Claims
                </>
              )}
            </button>
          </>
        )}

        {result && (
          <div className="space-y-3">
            <p className="flex items-center gap-2 rounded-xl border-[2.5px] border-cotiviti-ink bg-cotiviti-teal px-3 py-2 text-sm font-extrabold text-white">
              <CheckCircle2 size={18} strokeWidth={3} />
              {result.inserted_count} claim(s) uploaded successfully
            </p>

            {result.claim_ids.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {result.claim_ids.map((id) => (
                  <Link
                    key={id}
                    href={`/claims/${id}`}
                    className="chip-toon bg-cotiviti-violet px-2.5 py-1 text-xs text-white hover:brightness-110"
                  >
                    {id}
                  </Link>
                ))}
              </div>
            )}

            {result.errors.length > 0 && (
              <div className="rounded-xl border-[2.5px] border-cotiviti-ink bg-cotiviti-cream p-3">
                <p className="mb-1 flex items-center gap-1.5 text-xs font-extrabold text-cotiviti-coral">
                  <AlertTriangle size={14} strokeWidth={3} />
                  {result.errors.length} row(s) skipped
                </p>
                <ul className="space-y-0.5 text-xs font-semibold text-cotiviti-ink/70">
                  {result.errors.map((e, i) => (
                    <li key={i}>
                      Row {e.row}: {e.reason}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {result.analyses && (
              <p className="text-xs font-bold text-cotiviti-ink/60">
                AI analysis completed for {result.analyses.length} claim(s)
                {result.analysis_errors && result.analysis_errors.length > 0 &&
                  ` (${result.analysis_errors.length} failed)`}
                .
              </p>
            )}

            <div className="flex gap-2">
              <button
                onClick={() => {
                  setResult(null);
                  setFile(null);
                }}
                className="btn-toon flex-1 bg-cotiviti-lav px-4 py-2 text-sm font-bold text-cotiviti-ink"
              >
                Upload more
              </button>
              <button
                onClick={onClose}
                className="btn-toon flex-1 bg-cotiviti-magenta px-4 py-2 text-sm font-bold text-white"
              >
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
