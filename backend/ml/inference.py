"""Loads trained models once at import time and exposes simple inference
helpers used by the LangGraph agent's run_ml_signals node."""

import os

import joblib
import pandas as pd

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

_classifier = joblib.load(os.path.join(MODELS_DIR, "classifier.joblib"))
_predictor = joblib.load(os.path.join(MODELS_DIR, "predictor.joblib"))


def classify_claim(claim: dict, patient: dict) -> tuple[str, dict[str, float]]:
    row = pd.DataFrame([{
        "billed_amount": claim["billed_amount"],
        "length_of_stay": claim["length_of_stay"],
        "prior_claims_count": claim["prior_claims_count"],
        "age": patient["age"],
        "treatment_type": claim["treatment_type"],
        "procedure_code": claim["procedure_code"],
    }])
    label = _classifier.predict(row)[0]
    proba = _classifier.predict_proba(row)[0]
    proba_map = {cls: round(float(p), 4) for cls, p in zip(_classifier.classes_, proba)}
    return label, proba_map


def predict_payment(claim: dict, provider_avg_claim_amount: float) -> float:
    row = pd.DataFrame([{
        "billed_amount": claim["billed_amount"],
        "length_of_stay": claim["length_of_stay"],
        "provider_avg_claim_amount": provider_avg_claim_amount,
        "treatment_type": claim["treatment_type"],
    }])
    prediction = _predictor.predict(row)[0]
    return round(max(0.0, float(prediction)), 2)
