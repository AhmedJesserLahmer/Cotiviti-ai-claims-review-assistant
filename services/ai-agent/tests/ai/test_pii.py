import pytest

from ai_platform.guardrails.pii import redact_payload, redact_text


@pytest.mark.parametrize(
    "text, label",
    [
        ("ssn 123-45-6789 on file", "SSN"),
        ("contact jane.doe@example.com", "EMAIL"),
        ("call (555) 123-4567 today", "PHONE"),
        ("call +1 555.123.4567", "PHONE"),
        ("MRN: 00123456", "MRN"),
    ],
)
def test_redacts_common_pii(text, label):
    redacted, found = redact_text(text)
    assert f"[REDACTED_{label}]" in redacted
    assert label in found


@pytest.mark.parametrize("text", ["CPT10010", "ICD215", "billed 5200.0", "2026-01-15", "PRV0007", "CLM-UP-1a2b3c4d"])
def test_claim_codes_amounts_and_dates_are_untouched(text):
    assert redact_text(text) == (text, [])


def test_payload_redacts_sensitive_keys_and_nested_text():
    payload = {
        "claim_id": "CLM1",
        "patient": {"name": "Jane Doe", "age": 67, "notes": "reach at 555-123-4567"},
        "lines": [{"email": "x@y.com"}],
    }
    redacted, findings = redact_payload(payload)
    assert redacted["claim_id"] == "CLM1"
    assert redacted["patient"]["name"] == "[REDACTED]"
    assert redacted["patient"]["age"] == 67
    assert "[REDACTED_PHONE]" in redacted["patient"]["notes"]
    assert redacted["lines"][0]["email"] == "[REDACTED]"
    assert len(findings) == 3
    assert payload["patient"]["name"] == "Jane Doe"  # input is not mutated


def test_keep_keys_allows_business_names():
    redacted, findings = redact_payload({"name": "Acme Clinic"}, keep_keys=frozenset({"name"}))
    assert redacted == {"name": "Acme Clinic"} and not findings
