# Model or prompt regression / data drift

**Alerts:** `AIPolicyOverrideSpike` (guardrails escalate >40% of LLM decisions for 30 min),
`MLOutOfDistributionSurge` (>10% of scored claims unlike the training data).

## Policy override spike

Guardrails catching many LLM approvals means the model started approving things the ML
signals say are risky, or the reasoning cites ungrounded numbers. Safety is preserved
(escalations go to humans) but reviewer load rises.

1. Dashboard: which guardrails fire (*Guardrail events per minute*: `policy`,
   `grounding`, `llm_judge`).
2. Correlate with changes: a new `GROQ_MODEL`, a prompt version (`ai_metadata.prompt_versions`),
   or an `AI_PROMPT_TRAFFIC` experiment. `GET /analytics/ai-quality` → `agreement_by_prompt`.
3. Roll back the change ([rollback.md](rollback.md)) or set the experiment's traffic to 0.
4. Before re-enabling, run the evaluation gate on the candidate:
   `python -m evals.run_eval --mode live --max-unsafe 0`.

## Out-of-distribution surge

New claim types, providers or amounts the models never saw (data drift).

1. `ml_out_of_distribution_total` by `feature` shows which input drifted.
2. If expected (new procedure codes, a new region), retrain: trigger the training CronJob
   (`kubectl -n $NS create job --from=cronjob/claims-review-training retrain-$(date +%s)`),
   review the new version's metrics (`GET /v1/models` on ml-service), then activate it with
   `POST /v1/models/<version>/activate`.
3. If unexpected, it may be bad upstream data: check recent uploads in the audit log
   (`event_type = claims.upload`).
