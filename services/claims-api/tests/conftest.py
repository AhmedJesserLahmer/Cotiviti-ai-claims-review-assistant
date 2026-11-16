import pytest


@pytest.fixture(autouse=True)
def in_memory_audit_log(monkeypatch):
    """Unit tests never talk to MongoDB for audit entries."""
    try:
        from claims_common.audit_log import AuditLog
        from core import audit
        from tests.fakes import FakeDB
    except ImportError:  # service deps not installed: those tests are skipped anyway
        yield None
        return
    log = AuditLog(FakeDB(), hmac_key="t" * 32)
    monkeypatch.setattr(audit, "_audit", log)
    yield log
