import {
  AnalysisResult,
  Claim,
  ClaimUploadResponse,
  Provider,
  TimeseriesPoint,
} from "./types";

// Browser fetches must reach the API via a host-reachable URL; server-side
// (SSR / server components) fetches inside Docker use the internal service name.
const BROWSER_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const SERVER_BASE = process.env.INTERNAL_API_BASE_URL ?? BROWSER_BASE;
const BASE_URL = typeof window === "undefined" ? SERVER_BASE : BROWSER_BASE;

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Request failed (${res.status}): ${body}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listClaims: () => request<Claim[]>("/claims?limit=100"),
  getClaim: (claimId: string) => request<Claim>(`/claims/${claimId}`),
  analyzeClaim: (claimId: string) =>
    request<AnalysisResult>(`/claims/${claimId}/analyze`, { method: "POST" }),
  getAnalysis: (claimId: string) =>
    request<AnalysisResult>(`/claims/${claimId}/analysis`),
  listProviders: () => request<Provider[]>("/providers"),
  getProviderTimeseries: (providerId: string) =>
    request<TimeseriesPoint[]>(`/providers/${providerId}/timeseries?days=90`),
  uploadClaims: (file: File, autoAnalyze: boolean) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("auto_analyze", String(autoAnalyze));
    return request<ClaimUploadResponse>("/claims/upload", {
      method: "POST",
      body: formData,
    });
  },
};
