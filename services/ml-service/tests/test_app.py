import pytest

pytest.importorskip("motor")

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402


def test_liveness_and_no_cors():
    client = TestClient(main.app)
    r = client.get("/health/live", headers={"Origin": "http://evil.example"})
    assert r.json() == {"status": "alive"}
    assert "access-control-allow-origin" not in r.headers
