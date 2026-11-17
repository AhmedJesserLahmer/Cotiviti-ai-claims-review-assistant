"""Append-only, tamper-evident audit log.

Every entry gets a monotonically increasing ``seq`` (atomic counter) and an
HMAC-SHA256 ``signature`` over its canonical JSON, keyed by ``AUDIT_HMAC_KEY``:

* editing an entry breaks its signature,
* inserting a forged entry requires the key,
* deleting an entry leaves a gap in ``seq``.

``verify()`` checks all three. The application only ever inserts; in production the
database user should only have insert/find privileges on the collection.

Writes are fail-open: an audit failure is logged and counted
(``audit_write_failures_total``, alerted on) but does not fail the business request.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from prometheus_client import Counter

log = logging.getLogger("claims.audit")

AUDIT_WRITES = Counter("audit_writes_total", "Audit log entries written", ["event_type"])
AUDIT_FAILURES = Counter("audit_write_failures_total", "Audit log writes that failed", ["event_type"])

DEV_KEY = "dev-only-insecure-audit-key"
SIGNED_FIELDS = ("seq", "ts", "event_type", "actor", "subject", "data")


def _canonical(entry: dict[str, Any]) -> bytes:
    signed = {k: entry.get(k) for k in SIGNED_FIELDS}
    return json.dumps(signed, sort_keys=True, separators=(",", ":"), default=str).encode()


def sign(entry: dict[str, Any], key: str) -> str:
    return hmac.new(key.encode(), _canonical(entry), hashlib.sha256).hexdigest()


@dataclass
class VerificationReport:
    checked: int = 0
    valid: bool = True
    bad_signatures: list[int] = field(default_factory=list)
    missing_seqs: list[int] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "checked": self.checked, "valid": self.valid,
            "bad_signatures": self.bad_signatures[:100], "missing_seqs": self.missing_seqs[:100],
        }


class AuditLog:
    def __init__(self, db, *, hmac_key: str, collection: str = "audit_log", counters: str = "audit_counters"):
        if not hmac_key:
            raise ValueError("audit HMAC key is required")
        self._db = db
        self._key = hmac_key
        self._collection = collection
        self._counters = counters

    async def _next_seq(self) -> int:
        counter = await self._db[self._counters].find_one_and_update(
            {"_id": self._collection}, {"$inc": {"seq": 1}}, upsert=True, return_document=True
        )
        return int(counter["seq"])

    async def append(
        self, event_type: str, *, actor: str, subject: str, data: dict[str, Any] | None = None
    ) -> dict | None:
        try:
            entry = {
                "seq": await self._next_seq(),
                "ts": datetime.now(UTC).isoformat(),
                "event_type": event_type,
                "actor": actor,
                "subject": subject,
                "data": data or {},
            }
            entry["signature"] = sign(entry, self._key)
            await self._db[self._collection].insert_one(dict(entry))
        except Exception as exc:  # noqa: BLE001 - fail-open, but loudly
            AUDIT_FAILURES.labels(event_type).inc()
            log.error("audit write failed", extra={"event_type": event_type, "subject": subject, "error": str(exc)})
            return None
        AUDIT_WRITES.labels(event_type).inc()
        return entry

    async def verify(self, limit: int = 100_000) -> VerificationReport:
        report = VerificationReport()
        entries = await self._db[self._collection].find({}, {"_id": 0}).sort("seq", 1).to_list(length=limit)
        expected = 1
        for entry in entries:
            report.checked += 1
            seq = int(entry.get("seq", 0))
            if seq > expected:
                report.missing_seqs.extend(range(expected, seq))
            expected = seq + 1
            if not hmac.compare_digest(str(entry.get("signature", "")), sign(entry, self._key)):
                report.bad_signatures.append(seq)
        report.valid = not report.bad_signatures and not report.missing_seqs
        return report
