import pytest
from fastapi.testclient import TestClient

from claims_common.app import create_app
from claims_common.settings import ServiceSettings


def make(**settings):
    app = create_app(ServiceSettings(_env_file=None, **settings), title="t", cors=False, internal=True)

    @app.post("/v1/work")
    async def work():
        return {"ok": True}

    return TestClient(app)


def test_token_required_on_business_routes():
    client = make(internal_token="secret-token")
    assert client.post("/v1/work").status_code == 401
    assert client.post("/v1/work", headers={"X-Internal-Token": "wrong"}).status_code == 401
    assert client.post("/v1/work", headers={"X-Internal-Token": "secret-token"}).json() == {"ok": True}


def test_probes_and_metrics_are_open():
    client = make(internal_token="secret-token")
    assert client.get("/health/live").status_code == 200
    assert client.get("/metrics").status_code == 200


def test_unset_token_is_allowed_locally_but_not_in_production():
    assert make().post("/v1/work").status_code == 200
    with pytest.raises(RuntimeError, match="INTERNAL_TOKEN"):
        make(environment="prod")
