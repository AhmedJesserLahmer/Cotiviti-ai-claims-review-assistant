"""Startup seeding must not wipe a database that already holds (uploaded) claims."""

import pytest

pytest.importorskip("motor")

from data_gen import seed_mongo  # noqa: E402


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    async def estimated_document_count(self):
        return len(self.docs)

    async def delete_many(self, _filter):
        self.docs.clear()

    async def insert_many(self, records):
        self.docs.extend(records)


class FakeDB(dict):
    def __missing__(self, name):
        self[name] = FakeCollection()
        return self[name]


@pytest.fixture
def csv_dir(tmp_path, monkeypatch):
    for filename in seed_mongo.COLLECTIONS:
        (tmp_path / filename).write_text("id\n1\n2\n")
    monkeypatch.setattr(seed_mongo, "DATA_DIR", str(tmp_path))
    return tmp_path


async def test_if_empty_keeps_existing_claims_and_analyses(csv_dir, monkeypatch):
    db = FakeDB(
        claims=FakeCollection([{"claim_id": "UPLOADED-1"}]), claim_analyses=FakeCollection([{"claim_id": "UPLOADED-1"}])
    )
    monkeypatch.setattr(seed_mongo, "db", db)

    assert await seed_mongo.seed(only_if_empty=True) == {}
    assert db["claims"].docs == [{"claim_id": "UPLOADED-1"}]
    assert len(db["claim_analyses"].docs) == 1


async def test_if_empty_seeds_a_fresh_database(csv_dir, monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(seed_mongo, "db", db)

    counts = await seed_mongo.seed(only_if_empty=True)
    assert counts == {name: 2 for name in seed_mongo.COLLECTIONS.values()}


async def test_default_seed_is_a_full_reset(csv_dir, monkeypatch):
    db = FakeDB(
        claims=FakeCollection([{"claim_id": "UPLOADED-1"}]), claim_analyses=FakeCollection([{"claim_id": "UPLOADED-1"}])
    )
    monkeypatch.setattr(seed_mongo, "db", db)

    await seed_mongo.seed()
    assert db["claims"].docs == [{"id": 1}, {"id": 2}]
    assert db["claim_analyses"].docs == []
