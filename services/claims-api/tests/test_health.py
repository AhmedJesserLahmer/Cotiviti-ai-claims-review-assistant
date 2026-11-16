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


def test_ai_info_is_informational(monkeypatch):
    monkeypatch.setenv("AI_OFFLINE_MODE", "true")
    assert "llm_enabled" in health.ai_info()["ai"]
