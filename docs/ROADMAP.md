# Production Roadmap

This roadmap took the hackathon POC to a production-grade platform. It started as a
plan of 106 commits; this page now records what was delivered, commit by commit,
grouped by branch (each branch builds on the previous one).

The AI reliability principle: **the LLM never has the last word.** Every model output
is parsed, schema-validated, sanitized, grounded and cross-checked against the ML
signals by deterministic code that may only make a decision *more* conservative.
If no LLM is usable, a deterministic rule engine decides and the response says so
(see [ai-reliability.md](ai-reliability.md) and [adr/](adr)).

## Architecture

```
.
├── services/
│   ├── claims-api/      # public gateway: claims, uploads, jobs, feedback, auth, rate limits
│   ├── ai-agent/        # LangGraph agent + AI reliability layer + evaluation harness
│   └── ml-service/      # dataset, training, model registry, scoring, OOD guard
├── libs/python/claims-common/   # app factory, logging, metrics, tracing, resilience, auth, audit
├── frontend/            # Next.js reviewer dashboard
├── infra/               # compose, Helm, kind, Argo CD, Terraform, observability
├── e2e/ tests/load/     # Playwright and k6
└── docs/                # this roadmap, AI reliability, ADRs, runbooks
```

## Phase 0-1: Monorepo foundation and AI reliability layer (master)

Branch: `master`

- [x] 1. docs: add production roadmap and target architecture
- [x] 2. refactor: move backend into services/claims-api
- [x] 3. build: move compose file into infra/docker and include it from the root
- [x] 4. build: add root Makefile with memory-safe targets
- [x] 5. chore: add editorconfig and monorepo-wide gitignore rules
- [x] 6. build(claims-api): add pyproject with pytest and ruff config
- [x] 7. feat(ai): scaffold ai_platform package with error taxonomy
- [x] 8. feat(ai): add environment-driven AI settings
- [x] 9. feat(ai): add async retry with exponential backoff and full jitter
- [x] 10. feat(ai): add timeout guard for LLM calls
- [x] 11. feat(ai): add circuit breaker
- [x] 12. feat(ai): define LLM provider protocol and response types
- [x] 13. feat(ai): add Groq provider adapter with error mapping
- [x] 14. feat(ai): add scripted provider for tests and offline runs
- [x] 15. feat(ai): add resilient LLM client with model fallback chain
- [x] 16. feat(ai): add versioned prompt registry with hardened prompts
- [x] 17. feat(ai): add structured output schema for recommendations
- [x] 18. feat(ai): add tolerant JSON extraction and repair
- [x] 19. feat(ai): add validate-and-repair structured generation
- [x] 20. feat(ai): add PII redaction guardrail

## Phase 1: AI guardrails, fallback, audit and wiring

Branch: `feat/ai-* (8 stacked branches)`

- [x] 21. feat(ai): add prompt-injection guardrail for untrusted fields
- [x] 22. feat(ai): add output sanitization guardrail for reasoning
- [x] 23. feat(ai): add policy guardrail cross-checking ML signals
- [x] 24. feat(ai): add deterministic rule-based fallback recommender
- [x] 25. feat(ai): add AI run metadata audit trail
- [x] 26. feat(ai): add ClaimReviewAI facade orchestrating all layers
- [x] 27. refactor(agent): route LangGraph nodes through ClaimReviewAI
- [x] 28. feat(api): expose and persist AI run metadata on analyses

## Phase 2: Production basics

Branch: `feat/api-health-probes, feat/api-json-logging, feat/api-cors-config, feat/production-basics`

- [x] 29. feat(api): add liveness and readiness probes
- [x] 30. feat(api): add structured JSON logging and request IDs
- [x] 31. feat(api): make CORS origins configurable
- [x] 32. feat(frontend): show AI reliability panel on analyses
- [x] 33. build(claims-api): harden Dockerfile (non-root, healthcheck)
- [x] 34. docs: document AI reliability layer and monorepo layout

## Phase 3: Shared library and microservice extraction

Branch: `feat/microservices`

- [x] 35. build: add libs/python/claims-common package
- [x] 36. refactor(common): move JSON logging and request-id middleware to claims-common
- [x] 37. feat(common): add service settings base, app factory and health router
- [x] 38. refactor(common): move retry and circuit breaker to claims-common
- [x] 39. feat(common): add resilient async HTTP client for service-to-service calls
- [x] 40. feat(ai-agent): scaffold services/ai-agent service
- [x] 41. refactor(ai-agent): move agent, AI layer and ML code out of claims-api
- [x] 42. refactor(claims-api): drop ML and LLM dependencies from the gateway
- [x] 43. feat(ml-service): scaffold services/ml-service
- [x] 44. refactor(ml-service): move data generation, training and inference into ml-service
- [x] 45. feat(ml-service): add versioned model registry and /v1/models
- [x] 46. fix(ml-service): make training idempotent and pandas 3 compatible
- [x] 47. feat(ml-service): add feature validation and out-of-distribution guard
- [x] 48. test: add API contract tests between services
- [x] 49. feat(ai-agent): fall back to cached ML signals when ml-service is down
- [x] 50. feat(claims-api): add async analysis jobs (202 Accepted + job status)
- [x] 51. feat(claims-api): add Redis + arq worker for bulk analysis jobs
- [x] 52. build(infra): compose stack for three services, worker and redis

## Phase 4: AI layer v2

Branch: `feat/ai-layer-v2`

- [x] 53. feat(ai): add response cache for validated LLM results
- [x] 54. feat(ai): add token budget and cost accounting per run
- [x] 55. feat(security): add per-client rate limiting on analysis endpoints
- [x] 56. feat(ai): add OpenAI-compatible provider for cross-vendor fallback
- [x] 57. feat(ai): add hedged requests to cut tail latency
- [x] 58. feat(ai): add LLM-as-judge consistency check for approvals
- [x] 59. feat(ai): add grounding check for numbers cited in reasoning
- [x] 60. feat(ai): add confidence calibration and abstain-to-human threshold
- [x] 61. feat(ai): add reviewer feedback endpoint and AI quality analytics
- [x] 62. feat(ai): add offline evaluation harness with golden claim set
- [x] 63. ci(ai): gate merges on the AI evaluation
- [x] 64. feat(ai): add prompt A/B selection through the registry
- [x] 65. feat(ai): stream analysis progress over server-sent events
- [x] 66. feat(frontend): render streamed analysis progress live
- [x] 67. feat(frontend): add reviewer feedback controls

## Phase 5a: Observability

Branch: `feat/observability`

- [x] 68. feat(obs): add OpenTelemetry tracing across services
- [x] 69. feat(obs): add Prometheus metrics (LLM latency, fallbacks, guardrail hits, breaker state)
- [x] 70. feat(obs): expose /metrics and add a Prometheus scrape setup
- [x] 71. feat(obs): add Grafana dashboard for AI reliability
- [x] 72. feat(obs): add alert rules (fallback rate, breaker open, error budget)

## Phase 5b: Security

Branch: `feat/security`

- [x] 73. feat(security): add JWT authentication on claims-api
- [x] 74. feat(security): add reviewer and admin roles
- [x] 75. feat(security): add append-only, tamper-evident audit log
- [x] 76. feat(security): add upload size limits and CSV formula-injection protection
- [x] 77. feat(security): authenticate service-to-service calls
- [x] 78. feat(security): add HTTP security headers to every API
- [x] 79. ci(security): add pip-audit, npm audit and Dependabot
- [x] 80. ci(security): add Trivy scanning and secret scanning

## Phase 6: Kubernetes, Helm, GitOps and Terraform

Branch: `feat/infra-kubernetes`

- [x] 81. feat(helm): add claims-review chart foundation
- [x] 82. feat(helm): add workloads for every component
- [x] 83. feat(helm): add in-chart MongoDB and Redis for dev and staging
- [x] 84. feat(security): source secrets from External Secrets Operator
- [x] 85. feat(helm): add HorizontalPodAutoscalers
- [x] 86. feat(helm): add PodDisruptionBudgets
- [x] 87. feat(helm): add default-deny NetworkPolicies with explicit allow rules
- [x] 88. feat(helm): add Ingress with TLS via cert-manager
- [x] 89. feat(helm): run database seeding as a Helm hook Job
- [x] 90. feat(helm): add model-training CronJob with artifact volume
- [x] 91. feat(obs): add ServiceMonitors, PrometheusRule and dashboard ConfigMap to the chart
- [x] 92. feat(helm): add dev, staging and prod values files
- [x] 93. feat(helm): validate values with a JSON schema
- [x] 94. build(frontend): run the dashboard image as non-root
- [x] 95. feat(k8s): add kind cluster config and memory-capped local deploy script
- [x] 96. feat(k8s): add Argo CD project and applications (GitOps)
- [x] 97. feat(infra): add Terraform module for a managed AWS platform

## Phase 7: CI/CD, quality, tests and docs

Branch: `feat/ci-cd`

- [x] 98. style: add shared ruff config and fix lint findings
- [x] 99. ci: add lint and test workflow for python packages
- [x] 100. ci: add frontend lint, typecheck and build job
- [x] 101. ci: validate Helm, Kubernetes manifests, alert rules and Terraform
- [x] 102. style(infra): align Terraform files with terraform fmt
- [x] 103. ci: build, scan, sign and push images to GHCR
- [x] 104. ci: add per-component releases with release-please
- [x] 105. chore: add pre-commit hooks
- [x] 106. chore: add CODEOWNERS and pull request template
- [x] 107. test: add Playwright end-to-end tests against the compose stack
- [x] 108. test: add k6 load test for the analysis endpoint
- [x] 109. docs: add runbooks for every alert and for rollback
- [x] 110. docs: add architecture decision records
- [x] 111. docs: rewrite README architecture, layout, API and run sections

## Phase 8: Model quality

Branch: `feat/ml-model-quality`

- [x] 112. docs: update the roadmap to what was delivered
- [x] 113. feat(ml-service): replace the risk classifier, macro-F1 0.35 -> 0.60
- [x] 114. docs: add ADR 0010 for the risk classifier

## Phase 9: Findings from running the full stack

Branch: `fix/live-stack-findings`. Each fix comes from building the images, running the
stack against the real Groq API and testing it in the browser.

- [x] 115. build(ml-service): keep the local model registry out of the image
- [x] 116. build(infra): cap the MongoDB cache in the local compose stack
- [x] 117. fix(claims-api): reject uploaded fields longer than the scoring contract
- [x] 118. fix(ai-agent): answer 422 when a stored claim cannot be scored
- [x] 119. fix(ai): use asyncio.timeout so cancelled hedges end cleanly
- [x] 120. fix(frontend): format amounts with a fixed locale
- [x] 121. fix(ml-service): seed MongoDB at startup only when it is empty
- [x] 122. style(ai-agent): use union types in isinstance checks (ruff UP038)
- [x] 123. fix(ai): move off the Llama models Groq retired
- [x] 124. fix(frontend): resync package-lock.json with package.json
- [x] 125. fix(frontend): render LLM bold text and always show two-digit cents

## Next

- [ ] Ground recommendations in payer policy (coverage policies, coding edits) and cite them
- [ ] Check that the reasoning and the summary agree (an LLM judge for contradictions)
- [ ] A small human-labelled evaluation set for reasoning quality

- [ ] Replace the shared internal token with service-mesh mTLS identities (ADR 0008)
- [ ] Move the model registry to MLflow once several models are trained (ADR 0009)
- [ ] OIDC login in the dashboard itself (today: oauth2-proxy at the ingress)
- [ ] Database per service once write ownership needs different stores (ADR 0004)
