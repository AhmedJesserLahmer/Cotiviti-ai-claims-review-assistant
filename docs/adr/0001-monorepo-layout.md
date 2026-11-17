# 0001: Monorepo with services/, libs/, frontend/, infra/

**Context.** The POC was one FastAPI app. Production needs independently deployable
pieces with different scaling and dependency profiles: the gateway is I/O bound, the
agent waits on LLMs, the ML service needs scikit-learn and model files.

**Decision.** One repository: `services/{claims-api,ai-agent,ml-service}`, a shared
`libs/python/claims-common`, `frontend/`, and `infra/` (compose, Helm, Kubernetes,
Terraform, observability). Images are built from the repository root so they can install
the shared library. CI uses path filters so a change only builds and tests what it touches
(a change to the library re-tests every service).

**Consequences.** Atomic cross-service changes and one review per change; contract tests
(`claims_common.contracts` snapshot) replace the safety a separate API repository would
give. Cost: larger checkouts and the need for path-filtered CI.
