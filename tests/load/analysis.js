// k6 load test for the claims API and the AI analysis path.
//
//   k6 run tests/load/analysis.js                       # local stack
//   API_URL=https://api.claims.staging.example.com TOKEN=... k6 run tests/load/analysis.js
//
// Thresholds encode the SLOs: browsing p95 < 300 ms, analysis p95 < 8 s with the rule
// engine (offline) or < 30 s with a live LLM (set LIVE_LLM=true), errors < 1 %.
// 429s from the per-client rate limiter are expected under load and counted separately.
import http from "k6/http";
import { check, sleep } from "k6";
import { Counter, Trend } from "k6/metrics";

const API = __ENV.API_URL || "http://localhost:8000";
const LIVE = __ENV.LIVE_LLM === "true";
const headers = __ENV.TOKEN ? { Authorization: `Bearer ${__ENV.TOKEN}` } : {};

const analysisDuration = new Trend("analysis_duration", true);
const rateLimited = new Counter("rate_limited");
const ruleEngineDecisions = new Counter("rule_engine_decisions");

export const options = {
  scenarios: {
    browse: {
      executor: "ramping-vus",
      exec: "browse",
      stages: [
        { duration: "30s", target: 10 },
        { duration: "2m", target: 10 },
        { duration: "20s", target: 0 },
      ],
    },
    analyze: {
      executor: "constant-arrival-rate",
      exec: "analyze",
      rate: Number(__ENV.ANALYSES_PER_MINUTE || 20),
      timeUnit: "1m",
      duration: "3m",
      preAllocatedVUs: 5,
      maxVUs: 20,
    },
  },
  thresholds: {
    "http_req_duration{scenario:browse}": ["p(95)<300"],
    analysis_duration: [LIVE ? "p(95)<30000" : "p(95)<8000"],
    "http_req_failed{scenario:browse}": ["rate<0.01"],
    checks: ["rate>0.99"],
  },
};

export function setup() {
  const claims = http.get(`${API}/claims?limit=100`, { headers }).json();
  if (!Array.isArray(claims) || claims.length === 0) throw new Error("no claims; seed the database first");
  return { claimIds: claims.map((c) => c.claim_id) };
}

export function browse(data) {
  const list = http.get(`${API}/claims?limit=50`, { headers, tags: { name: "GET /claims" } });
  check(list, { "list 200": (r) => r.status === 200 });
  const id = data.claimIds[Math.floor(Math.random() * data.claimIds.length)];
  const one = http.get(`${API}/claims/${id}`, { headers, tags: { name: "GET /claims/{id}" } });
  check(one, { "claim 200": (r) => r.status === 200 });
  sleep(1);
}

export function analyze(data) {
  const id = data.claimIds[Math.floor(Math.random() * data.claimIds.length)];
  const response = http.post(`${API}/claims/${id}/analyze`, null, {
    headers,
    timeout: "90s",
    tags: { name: "POST /claims/{id}/analyze" },
  });
  if (response.status === 429) {
    rateLimited.add(1);
    return;
  }
  analysisDuration.add(response.timings.duration);
  check(response, {
    "analysis 200": (r) => r.status === 200,
    "valid decision": (r) => ["approve", "flag_for_review", "request_more_data"].includes(r.json("recommendation")),
    "has audit trail": (r) => r.json("ai_metadata.run_id") !== undefined,
  });
  if (response.status === 200 && response.json("ai_metadata.decision_source") === "rules") ruleEngineDecisions.add(1);
}
