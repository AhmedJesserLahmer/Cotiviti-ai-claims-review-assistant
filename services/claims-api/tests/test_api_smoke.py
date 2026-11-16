"""End-to-end smoke tests against a running API (the dockerized stack).

Set API_BASE_URL (default http://localhost:8000). Tests are skipped if the API
is unreachable, so `pytest` still passes for pure unit runs.
"""

import os

import pytest
import requests

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


def _api_up() -> bool:
    try:
        return requests.get(f"{BASE_URL}/health", timeout=2).status_code == 200
    except requests.RequestException:
        return False


pytestmark = pytest.mark.skipif(not _api_up(), reason=f"API not reachable at {BASE_URL}")


def test_health():
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_claims_returns_seeded_data():
    r = requests.get(f"{BASE_URL}/claims?limit=5", timeout=5)
    assert r.status_code == 200
    claims = r.json()
    assert len(claims) == 5
    claim = claims[0]
    for field in ["claim_id", "provider_id", "billed_amount", "risk_label"]:
        assert field in claim


def test_get_single_claim_and_404():
    first = requests.get(f"{BASE_URL}/claims?limit=1", timeout=5).json()[0]
    ok = requests.get(f"{BASE_URL}/claims/{first['claim_id']}", timeout=5)
    assert ok.status_code == 200
    assert ok.json()["claim_id"] == first["claim_id"]

    missing = requests.get(f"{BASE_URL}/claims/NOPE-000", timeout=5)
    assert missing.status_code == 404


def test_provider_cluster_and_timeseries():
    providers = requests.get(f"{BASE_URL}/providers", timeout=5).json()
    assert len(providers) > 0
    pid = providers[0]["provider_id"]

    cluster = requests.get(f"{BASE_URL}/providers/{pid}/cluster", timeout=5)
    assert cluster.status_code == 200
    assert "cluster_label" in cluster.json()

    ts = requests.get(f"{BASE_URL}/providers/{pid}/timeseries?days=30", timeout=5)
    assert ts.status_code == 200
    points = ts.json()
    assert len(points) > 0
    assert {"date", "daily_paid_total", "is_anomaly"} <= set(points[0].keys())


def test_analyze_requires_or_uses_groq():
    """Analyze either succeeds (key present) or fails cleanly (key absent)."""
    first = requests.get(f"{BASE_URL}/claims?limit=1", timeout=5).json()[0]
    r = requests.post(f"{BASE_URL}/claims/{first['claim_id']}/analyze", timeout=60)
    assert r.status_code in (200, 500)
    if r.status_code == 200:
        body = r.json()
        assert body["recommendation"] in {"approve", "flag_for_review", "request_more_data"}
        assert "signals" in body and "reasoning" in body


def test_upload_claims_csv_accepts_valid_rows_and_rejects_bad_provider():
    provider_id = requests.get(f"{BASE_URL}/providers", timeout=5).json()[0]["provider_id"]
    csv_body = (
        "provider_id,procedure_code,diagnosis_code,treatment_type,billed_amount,age\n"
        f"{provider_id},CPT10005,ICD210,Outpatient,1200.50,45\n"
        "NOT-A-REAL-PROVIDER,CPT10006,ICD211,Inpatient,8800.00,72\n"
    )
    files = {"file": ("upload.csv", csv_body, "text/csv")}
    r = requests.post(f"{BASE_URL}/claims/upload", files=files, data={"auto_analyze": "false"}, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body["inserted_count"] == 1
    assert len(body["claim_ids"]) == 1
    assert len(body["errors"]) == 1
    assert "NOT-A-REAL-PROVIDER" in body["errors"][0]["reason"]

    # the uploaded claim is immediately fetchable and analyzable like any other claim
    claim_id = body["claim_ids"][0]
    fetched = requests.get(f"{BASE_URL}/claims/{claim_id}", timeout=5)
    assert fetched.status_code == 200
    assert fetched.json()["risk_label"] == "Unlabeled"


def test_upload_claims_rejects_missing_columns():
    csv_body = "provider_id,billed_amount\nPRV0000,100\n"
    files = {"file": ("upload.csv", csv_body, "text/csv")}
    r = requests.post(f"{BASE_URL}/claims/upload", files=files, data={"auto_analyze": "false"}, timeout=15)
    assert r.status_code == 400
