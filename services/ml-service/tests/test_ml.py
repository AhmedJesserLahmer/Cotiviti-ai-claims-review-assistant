"""Unit tests for the trained models via the inference helpers."""

import pytest

from ml import registry

try:
    registry.current_version()
except registry.ModelNotFoundError:
    pytest.skip("models not trained yet (run: python -m ml.train_models)", allow_module_level=True)

SAMPLE_CLAIM = {
    "billed_amount": 5200.0,
    "length_of_stay": 3,
    "prior_claims_count": 2,
    "treatment_type": "Inpatient",
    "procedure_code": "CPT10010",
}
SAMPLE_PATIENT = {"age": 67}


def test_classify_claim_returns_valid_label_and_probs():
    from ml.inference import classify_claim

    label, proba = classify_claim(SAMPLE_CLAIM, SAMPLE_PATIENT)
    assert label in {"Low", "Medium", "High"}
    assert pytest.approx(sum(proba.values()), abs=1e-6) == 1.0
    assert all(0.0 <= v <= 1.0 for v in proba.values())


def test_predict_payment_is_non_negative():
    from ml.inference import predict_payment

    predicted = predict_payment(SAMPLE_CLAIM, provider_avg_claim_amount=4800.0)
    assert isinstance(predicted, float)
    assert predicted >= 0.0


def test_active_version_has_all_artifacts_and_metrics():
    path = registry.version_dir(registry.current_version())
    for name in registry.ARTIFACTS:
        assert (path / f"{name}.joblib").exists(), f"missing {name}"
    manifest = registry.load_bundle().manifest
    assert 0 <= manifest["metrics"]["classifier"]["accuracy"] <= 1
    assert manifest["metrics"]["predictor"]["mae"] >= 0
