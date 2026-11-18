# Architecture decision records

Short records of decisions that are hard to reverse or easy to question later.
Format: context, decision, consequences. Status is *accepted* unless noted.

| # | Decision |
|---|---|
| [0001](0001-monorepo-layout.md) | Monorepo with services/, libs/, frontend/, infra/ |
| [0002](0002-escalate-only-guardrails.md) | The LLM never has the last word: guardrails only escalate |
| [0003](0003-rule-engine-fallback.md) | Degrade to a deterministic rule engine instead of failing |
| [0004](0004-shared-database.md) | One MongoDB with per-collection ownership |
| [0005](0005-audit-log-hmac.md) | Audit log: HMAC + sequence numbers, not a hash chain |
| [0006](0006-cache-validated-results.md) | Cache validated LLM results at the facade |
| [0007](0007-per-replica-circuit-breakers.md) | Circuit breakers live in process memory |
| [0008](0008-internal-token-auth.md) | Shared-token service auth before a service mesh |
| [0009](0009-filesystem-model-registry.md) | Filesystem model registry on a shared volume |
| [0010](0010-risk-model.md) | Risk classifier: ordinal score with provider effects and macro-F1 cutoffs |
