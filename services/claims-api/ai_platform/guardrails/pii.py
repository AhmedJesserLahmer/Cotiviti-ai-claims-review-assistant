"""PII redaction applied to data before it is sent to a third-party LLM.

Two layers:
* key-based: fields whose name identifies a person (name, address, ssn, ...) are
  replaced entirely, whatever their content;
* pattern-based: free-text values are scanned for SSNs, emails, phone numbers and
  medical record numbers.

Pseudonymous identifiers (patient_id, claim_id) are kept: the model needs them to
refer to the claim and they are meaningless outside our database.
"""

from __future__ import annotations

import re
from typing import Any

from ai_platform.guardrails.base import GuardrailFinding

SENSITIVE_KEYS = frozenset({
    "name", "patient_name", "first_name", "last_name", "full_name",
    "address", "street", "city", "zip", "zip_code", "postal_code",
    "ssn", "social_security_number", "phone", "phone_number", "email",
    "dob", "date_of_birth", "birth_date", "mrn", "medical_record_number",
})

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("PHONE", re.compile(r"(?<![\w-])(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?![\w-])")),
    ("MRN", re.compile(r"\bMRN[:#\s-]*\d{5,}\b", re.IGNORECASE)),
]


def redact_text(text: str) -> tuple[str, list[str]]:
    """Return the text with PII replaced by [REDACTED_<TYPE>] and the types found."""
    found: list[str] = []
    for label, pattern in _PATTERNS:
        text, count = pattern.subn(f"[REDACTED_{label}]", text)
        if count:
            found.append(label)
    return text, found


def redact_payload(
    data: Any, *, keep_keys: frozenset[str] = frozenset(), _path: str = ""
) -> tuple[Any, list[GuardrailFinding]]:
    """Recursively redact a JSON-like structure. Returns (redacted copy, findings)."""
    findings: list[GuardrailFinding] = []

    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            path = f"{_path}.{key}" if _path else str(key)
            if str(key).lower() in SENSITIVE_KEYS and str(key) not in keep_keys and value not in (None, ""):
                result[key] = "[REDACTED]"
                findings.append(GuardrailFinding("pii", "redacted", f"field '{path}' removed"))
                continue
            result[key], nested = redact_payload(value, keep_keys=keep_keys, _path=path)
            findings.extend(nested)
        return result, findings

    if isinstance(data, list):
        items = []
        for index, value in enumerate(data):
            item, nested = redact_payload(value, keep_keys=keep_keys, _path=f"{_path}[{index}]")
            items.append(item)
            findings.extend(nested)
        return items, findings

    if isinstance(data, str):
        redacted, types = redact_text(data)
        if types:
            findings.append(GuardrailFinding("pii", "redacted", f"{', '.join(types)} in '{_path or 'text'}'"))
        return redacted, findings

    return data, findings
