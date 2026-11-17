# Prompt-injection burst

**Alert:** `AIPromptInjectionBurst`: more than 5 blocked injection attempts in 10 minutes.

**Meaning:** uploaded claim fields contain instructions aimed at the LLM ("ignore previous
instructions", chat markup, decision steering). The guardrail removed the text, the run
is flagged, and the policy refuses to auto-approve those claims. No action is required
for safety; the alert exists because it signals a malicious or compromised uploader.

## Actions

1. Find the uploads: audit log entries `claims.upload` around the alert time give the
   actor (token subject) and claim ids; `ai_metadata.guardrail_events` shows which field
   matched which pattern.
2. If the uploader is an integration, contact its owner; if it is a user account, consider
   revoking it at the identity provider.
3. If it is a false positive (legitimate text matching a pattern), add a test case to
   `tests/ai/test_injection.py` and narrow the pattern in `guardrails/injection.py`.
