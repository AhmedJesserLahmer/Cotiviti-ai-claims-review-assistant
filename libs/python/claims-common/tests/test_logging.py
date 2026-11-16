import json
import logging

import pytest

pytest.importorskip("fastapi")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from claims_common.logging import JsonFormatter, RequestContextMiddleware, request_id_var  # noqa: E402


def make_app():
    app = FastAPI()

    @app.get("/ping")
    async def ping():
        logging.getLogger("t").info("inside", extra={"claim_id": "C1"})
        return {"request_id": request_id_var.get()}

    app.add_middleware(RequestContextMiddleware)
    return TestClient(app)


def test_generates_and_echoes_request_id():
    r = make_app().get("/ping")
    rid = r.headers["x-request-id"]
    assert len(rid) == 32 and r.json()["request_id"] == rid


def test_propagates_valid_incoming_id_and_rejects_garbage():
    c = make_app()
    assert c.get("/ping", headers={"X-Request-ID": "abc-123"}).headers["x-request-id"] == "abc-123"
    assert c.get("/ping", headers={"X-Request-ID": "bad id\n<script>"}).headers["x-request-id"] != "bad id\n<script>"


def test_json_formatter_includes_context_and_extras():
    token = request_id_var.set("rid-1")
    try:
        record = logging.makeLogRecord({"name": "x", "levelname": "INFO", "msg": "hello %s", "args": ("you",)})
        record.claim_id = "C1"
        line = json.loads(JsonFormatter().format(record))
    finally:
        request_id_var.reset(token)
    assert line["msg"] == "hello you" and line["request_id"] == "rid-1" and line["claim_id"] == "C1"
    assert line["level"] == "info"
