## What and why

<!-- One or two sentences. Link the issue. -->

## How it was tested

- [ ] Unit tests (`make test`)
- [ ] AI evaluation gate (`make eval`) for changes to prompts, guardrails, policy or models
- [ ] Helm (`make helm-lint`) for changes under `infra/`

## AI safety checklist (prompts, guardrails, policy, models)

- [ ] Prompt changes bump the prompt version in `ai_platform/prompts.py`
- [ ] Guardrails still only escalate towards manual review (never approve or deny)
- [ ] No new data is sent to the LLM without passing the PII and injection guardrails
- [ ] New wire fields are optional (rolling deploys); the contract snapshot test is updated

## Operations

- [ ] New configuration is documented in `.env.example` and the chart values
- [ ] New alerts link a runbook in `docs/runbooks/`
