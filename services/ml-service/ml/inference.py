"""Inference helpers on top of the active registry version.

The bundle is loaded lazily on first use (so the service can start and report
"not ready" instead of crashing when no model exists) and can be reloaded after a
new version is activated.
"""

from __future__ import annotations

import pandas as pd

from ml.registry import ModelBundle, load_bundle

_bundle: ModelBundle | None = None


def get_bundle() -> ModelBundle:
    global _bundle
    if _bundle is None:
        _bundle = load_bundle()
    return _bundle


def reload_bundle(version: str | None = None) -> ModelBundle:
    global _bundle
    _bundle = load_bundle(version)
    return _bundle


def classify_claim(claim: dict, patient: dict) -> tuple[str, dict[str, float]]:
    classifier = get_bundle().classifier
    row = pd.DataFrame([{
        "billed_amount": claim["billed_amount"],
        "length_of_stay": claim["length_of_stay"],
        "prior_claims_count": claim["prior_claims_count"],
        "age": patient["age"],
        "treatment_type": claim["treatment_type"],
        "procedure_code": claim["procedure_code"],
    }])
    label = classifier.predict(row)[0]
    proba = classifier.predict_proba(row)[0]
    proba_map = {cls: round(float(p), 4) for cls, p in zip(classifier.classes_, proba, strict=True)}
    return label, proba_map


def predict_payment(claim: dict, provider_avg_claim_amount: float) -> float:
    row = pd.DataFrame([{
        "billed_amount": claim["billed_amount"],
        "length_of_stay": claim["length_of_stay"],
        "provider_avg_claim_amount": provider_avg_claim_amount,
        "treatment_type": claim["treatment_type"],
    }])
    prediction = get_bundle().predictor.predict(row)[0]
    return round(max(0.0, float(prediction)), 2)


def active_version() -> str:
    return get_bundle().version


def ood_flags(features: dict) -> list[str]:
    from ml.ood import check

    return check(features, get_bundle().manifest.get("feature_profile"))
