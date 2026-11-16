"""Output guardrail for free-text reasoning returned by the LLM.

The reasoning is stored in MongoDB and rendered in the reviewer dashboard, so it is
treated like any other untrusted input:

* empty output is rejected (the caller falls back to deterministic reasoning),
* HTML tags and markdown headers are stripped (no markup injection into the UI),
* PII the model may have echoed is redacted,
* fragments of our system prompt are detected (prompt leakage) and the text replaced,
* refusals ("As an AI ...") are flagged so the reviewer knows the reasoning is weak,
* length is capped on a line boundary.
"""

from __future__ import annotations

import re

from ai_platform.errors import OutputValidationError
from ai_platform.guardrails.base import GuardrailFinding
from ai_platform.guardrails.pii import redact_text
from ai_platform.prompts import UNTRUSTED_DATA_NOTICE

_HTML_TAG_RE = re.compile(r"<[^>\n]{1,200}>")
_MD_HEADER_RE = re.compile(r"^\s{0,3}#{1,6}\s+", re.MULTILINE)
_BLANK_LINES_RE = re.compile(r"\n{3,}")
_REFUSAL_RE = re.compile(r"\b(as an ai\b|i (cannot|can't|am unable to) (help|assist|provide))", re.IGNORECASE)
_LEAK_MARKERS = (UNTRUSTED_DATA_NOTICE[:60].lower(), "<claim_data>", "you are a healthcare claims review analyst")


def sanitize_reasoning(text: str, *, max_chars: int = 2500) -> tuple[str, list[GuardrailFinding]]:
    """Return (safe reasoning text, findings). Raises OutputValidationError if unusable."""
    if not isinstance(text, str) or not text.strip():
        raise OutputValidationError("model returned empty reasoning")

    findings: list[GuardrailFinding] = []
    cleaned = text.strip()

    lowered = cleaned.lower()
    if any(marker in lowered for marker in _LEAK_MARKERS):
        raise OutputValidationError("model output echoed system instructions (prompt leakage)")

    without_markup = _MD_HEADER_RE.sub("", _HTML_TAG_RE.sub("", cleaned))
    if without_markup != cleaned:
        findings.append(GuardrailFinding("output_sanitizer", "sanitized", "markup removed from reasoning"))
    cleaned = _BLANK_LINES_RE.sub("\n\n", without_markup).strip()

    cleaned, pii_types = redact_text(cleaned)
    if pii_types:
        findings.append(GuardrailFinding("pii", "redacted", f"{', '.join(pii_types)} in reasoning"))

    if _REFUSAL_RE.search(cleaned):
        findings.append(GuardrailFinding("output_quality", "warned", "reasoning contains a refusal"))

    if len(cleaned) > max_chars:
        cut = cleaned.rfind("\n", 0, max_chars)
        cleaned = cleaned[: cut if cut > max_chars // 2 else max_chars].rstrip() + "\n…"
        findings.append(GuardrailFinding("output_sanitizer", "sanitized", f"reasoning truncated to {max_chars} chars"))

    if not cleaned.strip():
        raise OutputValidationError("reasoning empty after sanitization")
    return cleaned, findings
