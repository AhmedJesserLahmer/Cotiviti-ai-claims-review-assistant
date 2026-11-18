# Circuit breaker open

**Alert:** `AICircuitOpen`: a provider/model circuit has been open for 5 minutes.

**Meaning:** that model failed `AI_CIRCUIT_FAILURE_THRESHOLD` times in a row and is skipped
without being called. Traffic goes to the next model in the chain (`AI_FALLBACK_MODELS`,
then the OpenAI-compatible fallback if configured, then the rule engine).

## Actions

1. Identify the breaker label (`groq/<model>`) in the alert and check that model's error
   ratio on the dashboard.
2. If only one model is affected and fallbacks are healthy, no action is needed: the
   breaker probes every `AI_CIRCUIT_RECOVERY_S` and closes on success.
3. If the model was retired by the provider (`NotFoundError` / `model_decommissioned` in
   `ai_metadata.attempts[].error`), change `GROQ_MODEL` / `AI_FALLBACK_MODELS` in the
   values and roll out. Bump nothing else: prompt versions stay the same.
4. If every circuit is open, follow [llm-outage.md](llm-outage.md).
