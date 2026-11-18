"""Process-wide tamper-evident audit log (see claims_common.audit_log)."""

from claims_common.audit_log import AuditLog
from core.config import settings
from db.mongo import db

_audit: AuditLog | None = None


def get_audit_log() -> AuditLog:
    global _audit
    if _audit is None:
        _audit = AuditLog(db, hmac_key=settings.audit_key())
    return _audit
