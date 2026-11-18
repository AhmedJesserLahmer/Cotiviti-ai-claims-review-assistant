# Runbooks

One page per alert in `infra/helm/claims-review/files/prometheus/ai-alerts.yml`.
Each page says what the alert means, what users experience, how to confirm it, and
what to do. Commands assume `NS=claims-review-prod` and `kubectl` access.

| Alert | Page |
|---|---|
| ClaimsApiErrorBudgetFastBurn / SlowBurn | [api-errors.md](api-errors.md) |
| ServiceDown | [service-down.md](service-down.md) |
| AIDegradedToRuleEngine(Critical), AILLMLatencyHigh | [llm-outage.md](llm-outage.md) |
| AICircuitOpen | [circuit-open.md](circuit-open.md) |
| AIPolicyOverrideSpike, MLOutOfDistributionSurge | [model-regression.md](model-regression.md) |
| AIPromptInjectionBurst | [prompt-injection.md](prompt-injection.md) |
| AISpendHigh | [llm-cost.md](llm-cost.md) |
| AuditLogWriteFailures | [audit-log.md](audit-log.md) |

Rollback of any deployment: [rollback.md](rollback.md).
