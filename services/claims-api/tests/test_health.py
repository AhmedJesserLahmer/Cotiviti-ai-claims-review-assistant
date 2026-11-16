import pytest

pytest.importorskip("motor")

from routers import health  # noqa: E402


class FakeDB:
    def __init__(self, fail=False):
        self.fail = fail

    async def command(self, name):
        if self.fail:
            raise ConnectionError("mongo unreachable")
        return {"ok": 1}


async def test_mongo_check(monkeypatch):
    monkeypatch.setattr(health, "db", FakeDB())
    await health.mongo_ping()
    monkeypatch.setattr(health, "db", FakeDB(fail=True))
    with pytest.raises(ConnectionError):
        await health.mongo_ping()


def test_dependency_info_reports_ai_agent():
    deps = health.dependency_info()["dependencies"]
    assert [d["service"] for d in deps] == ["ai-agent", "ml-service"]
