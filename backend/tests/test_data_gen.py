"""Unit tests for the synthetic data generator (no external services needed)."""

import numpy as np
from faker import Faker

from data_gen import generate_data as gd


def _rng_fake():
    rng = np.random.default_rng(0)
    Faker.seed(0)
    return rng, Faker()


def test_providers_shape_and_columns():
    rng, fake = _rng_fake()
    providers = gd.generate_providers(rng, fake)
    assert len(providers) == gd.N_PROVIDERS
    for col in ["provider_id", "specialty", "region", "avg_claim_amount", "risk_baseline"]:
        assert col in providers.columns
    assert providers["provider_id"].is_unique


def test_claims_have_valid_risk_labels_and_links():
    rng, fake = _rng_fake()
    providers = gd.generate_providers(rng, fake)
    patients = gd.generate_patients(rng, fake)
    claims = gd.generate_claims(rng, providers, patients)

    assert len(claims) == gd.N_CLAIMS
    assert set(claims["risk_label"].unique()).issubset({"Low", "Medium", "High"})
    # every claim references a real provider and patient
    assert set(claims["provider_id"]).issubset(set(providers["provider_id"]))
    assert set(claims["patient_id"]).issubset(set(patients["patient_id"]))
    # denied claims are never paid
    denied = claims[claims["status"] == "Denied"]
    assert (denied["paid_amount"] == 0).all()


def test_timeseries_covers_all_providers():
    rng, fake = _rng_fake()
    providers = gd.generate_providers(rng, fake)
    ts = gd.generate_timeseries(rng, providers)
    assert set(ts["provider_id"].unique()) == set(providers["provider_id"])
    assert (ts["daily_claim_count"] >= 0).all()
    assert (ts["daily_paid_total"] >= 0).all()
