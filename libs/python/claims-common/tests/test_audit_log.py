import copy

import pytest

from claims_common.audit_log import AuditLog


class Cursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, key, direction):
        self.docs = sorted(self.docs, key=lambda d: d[key], reverse=direction < 0)
        return self

    async def to_list(self, length=None):
        return [copy.deepcopy(d) for d in self.docs[:length]]


class Collection:
    def __init__(self):
        self.docs = []

    async def insert_one(self, doc):
        self.docs.append(copy.deepcopy(doc))

    async def find_one_and_update(self, query, update, upsert=False, return_document=False):
        for doc in self.docs:
            if doc["_id"] == query["_id"]:
                doc["seq"] += update["$inc"]["seq"]
                return dict(doc)
        self.docs.append({"_id": query["_id"], "seq": update["$inc"]["seq"]})
        return dict(self.docs[-1])

    def find(self, query, projection=None):
        return Cursor(self.docs)


class DB(dict):
    def __missing__(self, key):
        self[key] = Collection()
        return self[key]


async def _log_with(n):
    db = DB()
    log = AuditLog(db, hmac_key="k" * 32)
    for i in range(n):
        await log.append("ai.decision", actor="ai-agent", subject=f"C{i}", data={"recommendation": "approve"})
    return db, log


async def test_entries_are_sequenced_signed_and_verify():
    db, log = await _log_with(3)
    assert [d["seq"] for d in db["audit_log"].docs] == [1, 2, 3]
    report = await log.verify()
    assert report.valid and report.checked == 3


async def test_tampering_and_deletion_are_detected():
    db, log = await _log_with(4)
    db["audit_log"].docs[1]["data"]["recommendation"] = "deny"   # edit
    del db["audit_log"].docs[2]                                   # delete seq 3
    report = await log.verify()
    assert not report.valid and report.bad_signatures == [2] and report.missing_seqs == [3]


async def test_wrong_key_cannot_forge():
    db, _ = await _log_with(1)
    assert (await AuditLog(db, hmac_key="other" * 8).verify()).bad_signatures == [1]


async def test_failures_are_fail_open():
    class Broken(DB):
        def __missing__(self, key):
            raise ConnectionError("db down")

    assert await AuditLog(Broken(), hmac_key="k").append("x", actor="a", subject="s") is None
    with pytest.raises(ValueError):
        AuditLog(DB(), hmac_key="")
