"""Training regressions: idempotent retraining and pandas-version-safe features."""

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn")

from ml.train_models import train_anomaly_detector, train_clustering  # noqa: E402


def _timeseries():
    rng = np.random.default_rng(0)
    rows = []
    for pid in ["P1", "P2"]:
        for day in range(30):
            rows.append({"provider_id": pid, "date": f"2026-01-{day + 1:02d}",
                         "daily_claim_count": int(rng.integers(1, 10)), "daily_paid_total": float(rng.uniform(100, 900))})
    return pd.DataFrame(rows)


def test_anomaly_detector_keeps_provider_id_and_is_idempotent():
    first, _ = train_anomaly_detector(_timeseries())
    assert "provider_id" in first.columns and len(first) == 60
    again, _ = train_anomaly_detector(first.drop(columns=["count_z", "amount_z"]))
    assert list(again.columns) == list(first.columns)
    assert again["anomaly_score"].round(6).tolist() == first["anomaly_score"].round(6).tolist()


def test_clustering_is_idempotent():
    rng = np.random.default_rng(1)
    providers = pd.DataFrame({"provider_id": [f"P{i}" for i in range(8)], "name": "x"})
    claims = pd.DataFrame({
        "claim_id": range(80), "provider_id": [f"P{i % 8}" for i in range(80)],
        "billed_amount": rng.uniform(100, 5000, 80), "status": rng.choice(["Paid", "Denied"], 80),
        "length_of_stay": rng.integers(0, 5, 80),
    })
    once = train_clustering(claims, providers)[0]
    twice = train_clustering(claims, once)[0]
    assert list(twice.columns) == list(once.columns)
    assert not any(c.endswith(("_x", "_y")) for c in twice.columns)
