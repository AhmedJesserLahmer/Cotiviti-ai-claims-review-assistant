# Production Roadmap

This roadmap takes the hackathon POC to a production-grade platform. Each line is one
commit. The roadmap is split into phases so the repository stays runnable after every
commit.

Legend: `[x]` done · `[ ]` planned

## Target architecture

```
.
├── services/
│   ├── claims-api/      # public REST gateway: claims, providers, uploads, auth
│   ├── ml-service/      # model training, model registry, inference endpoints
│   └── ai-agent/        # LangGraph agent + AI reliability layer (guardrails, fallbacks)
├── libs/
│   └── python/claims-common/   # logging, config, resilience, health, http client
├── frontend/            # Next.js reviewer dashboard
├── infra/
│   ├── docker/          # docker compose for local development
│   ├── helm/            # Helm charts for Kubernetes
│   └── k8s/             # cluster-level manifests (kind, GitOps, policies)
└── docs/                # architecture, runbooks, ADRs
```

The AI reliability principle: **the LLM never has the last word.** Every model output
is parsed, schema-validated, sanitized, and cross-checked against the ML signals by a
deterministic policy. Guardrails may only make a decision *more* conservative
(towards human review), never less. If every LLM is unavailable, a deterministic
rule engine produces the decision, and the response says so.

---

## Phase 0: Monorepo foundation

- [x] 1. docs: add production roadmap and target architecture
- [x] 2. refactor: move backend into services/claims-api
- [x] 3. build: move compose file into infra/docker and include it from the root
- [x] 4. build: add root Makefile with memory-safe targets
- [x] 5. chore: add editorconfig and monorepo-wide gitignore rules
- [x] 6. build(claims-api): add pyproject with pytest and ruff config

## Phase 1: AI reliability layer (`ai_platform`)

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
- [x] 21. feat(ai): add prompt-injection guardrail for untrusted fields
- [x] 22. feat(ai): add output sanitization guardrail for reasoning
- [x] 23. feat(ai): add policy guardrail cross-checking ML signals
- [x] 24. feat(ai): add deterministic rule-based fallback recommender
- [x] 25. feat(ai): add AI run metadata audit trail
- [x] 26. feat(ai): add ClaimReviewAI facade orchestrating all layers
- [x] 27. refactor(agent): route LangGraph nodes through ClaimReviewAI
- [x] 28. feat(api): expose and persist AI run metadata on analyses

## Phase 2: Production basics

- [ ] 29. feat(api): add liveness and readiness probes
- [ ] 30. feat(api): add structured JSON logging and request IDs
- [ ] 31. feat(api): make CORS origins configurable
- [ ] 32. feat(frontend): show AI reliability panel on analyses
- [ ] 33. build(claims-api): harden Dockerfile (non-root, healthcheck)
- [ ] 34. feat(helm): add claims-review Helm chart for api and frontend
- [ ] 35. docs: document AI reliability layer and monorepo layout

## Phase 3: Shared library and service extraction

- [ ] 36. build: add libs/python/claims-common package
- [ ] 37. refactor(common): move JSON logging and request-id middleware to claims-common
- [ ] 38. feat(common): add shared settings base and health router factory
- [ ] 39. refactor(common): move resilience primitives (retry, breaker, timeout) to claims-common
- [ ] 40. feat(common): add resilient async HTTP client (httpx) for service-to-service calls
- [ ] 41. feat(ml-service): scaffold services/ml-service FastAPI app
- [ ] 42. refactor(ml-service): move data generation and training into ml-service
- [ ] 43. feat(ml-service): add /v1/classify and /v1/predict-payment endpoints
- [ ] 44. feat(ml-service): add versioned model registry and /v1/models
- [ ] 45. feat(ml-service): add feature validation and out-of-distribution guard
- [ ] 46. test(ml-service): add API contract tests
- [ ] 47. feat(ai-agent): scaffold services/ai-agent service
- [ ] 48. refactor(ai-agent): move LangGraph agent and ai_platform into ai-agent
- [ ] 49. feat(ai-agent): add /v1/analyses endpoint
- [ ] 50. feat(ai-agent): fetch ML signals from ml-service with cached fallback
- [ ] 51. refactor(claims-api): call ai-agent over HTTP instead of in-process
- [ ] 52. refactor(claims-api): drop ML and LLM dependencies from the gateway
- [ ] 53. feat(claims-api): async analysis jobs (202 Accepted + job status)
- [ ] 54. feat: add Redis + arq worker for bulk auto-analyze
- [ ] 55. build(infra): update compose for three services and redis

## Phase 4: AI layer v2

- [ ] 56. feat(ai): add response cache keyed by claim and signal hash
- [ ] 57. feat(ai): add token budget and cost accounting per run
- [ ] 58. feat(ai): add per-client rate limiting on analysis endpoints
- [ ] 59. feat(ai): add OpenAI-compatible provider for cross-vendor fallback
- [ ] 60. feat(ai): add hedged requests to cut tail latency
- [ ] 61. feat(ai): add LLM-as-judge consistency check (reasoning vs decision)
- [ ] 62. feat(ai): add grounding check: numbers cited must match ML signals
- [ ] 63. feat(ai): add confidence calibration and abstain-to-human threshold
- [ ] 64. feat(ai): add reviewer feedback endpoint (agree / override)
- [ ] 65. feat(ai): add offline evaluation harness with golden claim set
- [ ] 66. ci(ai): gate merges on evaluation metrics
- [ ] 67. feat(ai): add prompt A/B selection through the registry
- [ ] 68. feat(ai): stream reasoning over server-sent events
- [ ] 69. feat(frontend): render streamed reasoning live
- [ ] 70. feat(frontend): add reviewer feedback controls

## Phase 5: Observability and security

- [ ] 71. feat(obs): add OpenTelemetry tracing across services
- [ ] 72. feat(obs): add Prometheus metrics (LLM latency, fallbacks, guardrail hits, breaker state)
- [ ] 73. feat(obs): expose /metrics and add ServiceMonitor
- [ ] 74. feat(obs): add Grafana dashboard for AI reliability
- [ ] 75. feat(obs): add alert rules (fallback rate, breaker open, error budget)
- [ ] 76. feat(security): add JWT authentication on claims-api
- [ ] 77. feat(security): add reviewer / admin roles
- [ ] 78. feat(security): add append-only audit log for AI decisions
- [ ] 79. feat(security): add upload size limits and CSV formula-injection protection
- [ ] 80. feat(security): source secrets from External Secrets Operator
- [ ] 81. ci(security): add pip-audit and npm audit
- [ ] 82. ci(security): add Trivy image scanning

## Phase 6: Kubernetes and Helm

- [ ] 83. feat(helm): add ml-service and ai-agent templates
- [ ] 84. feat(helm): add HorizontalPodAutoscalers
- [ ] 85. feat(helm): add PodDisruptionBudgets
- [ ] 86. feat(helm): add default-deny NetworkPolicies with explicit allow rules
- [ ] 87. feat(helm): add Ingress with TLS via cert-manager
- [ ] 88. feat(helm): add optional MongoDB dependency
- [ ] 89. feat(helm): add optional Redis dependency
- [ ] 90. feat(helm): run database seeding as a Helm hook Job
- [ ] 91. feat(helm): add model-training CronJob with artifact volume
- [ ] 92. feat(helm): add dev / staging / prod values files
- [ ] 93. feat(k8s): add kind cluster config and memory-capped local deploy script
- [ ] 94. ci(helm): add helm lint, kubeconform and chart-testing
- [ ] 95. feat(k8s): add Argo CD Application manifests (GitOps)
- [ ] 96. feat(infra): add Terraform module for a managed cluster

## Phase 7: CI/CD and developer experience

- [ ] 97. ci: add lint and test workflow for python services
- [ ] 98. ci: add frontend lint, typecheck and build workflow
- [ ] 99. ci: add path-filtered builds per service
- [ ] 100. ci: build and push images to GHCR with SBOM
- [ ] 101. ci: add per-service release workflow with semantic versions
- [ ] 102. chore: add pre-commit hooks (ruff, prettier, helm lint)
- [ ] 103. test: add Playwright end-to-end tests against the compose stack
- [ ] 104. test: add k6 load test for the analysis endpoint
- [ ] 105. docs: add runbooks (LLM outage, breaker open, rollback)
- [ ] 106. docs: add architecture decision records
