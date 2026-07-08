"""Generates synthetic healthcare claims data (providers, patients, claims,
provider payment time-series) for the Claims Review Assistant POC.

Run with: python -m data_gen.generate_data
Writes CSVs to backend/data/.
"""

import os

import numpy as np
import pandas as pd
from faker import Faker

SEED = 42
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

N_PROVIDERS = 30
N_PATIENTS = 200
N_CLAIMS = 1500
TIMESERIES_DAYS = 180

SPECIALTIES = [
    "Cardiology", "Orthopedics", "Internal Medicine", "Oncology",
    "Radiology", "General Surgery", "Neurology", "Pediatrics",
]
REGIONS = ["Northeast", "Southeast", "Midwest", "Southwest", "West"]
TREATMENT_TYPES = ["Inpatient", "Outpatient", "Emergency", "Telehealth", "Diagnostic"]
PROCEDURE_CODES = [f"CPT{code}" for code in np.arange(10000, 10030)]
DIAGNOSIS_CODES = [f"ICD{code}" for code in np.arange(200, 230)]
STATUSES = ["Paid", "Denied", "Pending"]


def generate_providers(rng: np.random.Generator, fake: Faker) -> pd.DataFrame:
    rows = []
    for i in range(N_PROVIDERS):
        risk_baseline = rng.uniform(0.05, 0.6)
        rows.append({
            "provider_id": f"PRV{i:04d}",
            "name": fake.company() + " Clinic",
            "specialty": rng.choice(SPECIALTIES),
            "region": rng.choice(REGIONS),
            "avg_claim_amount": round(rng.uniform(200, 8000), 2),
            "risk_baseline": round(risk_baseline, 3),
        })
    return pd.DataFrame(rows)


def generate_patients(rng: np.random.Generator, fake: Faker) -> pd.DataFrame:
    rows = []
    for i in range(N_PATIENTS):
        rows.append({
            "patient_id": f"PAT{i:04d}",
            "name": fake.name(),
            "age": int(rng.integers(1, 95)),
            "gender": rng.choice(["F", "M", "Other"]),
            "chronic_conditions": int(rng.poisson(1.2)),
        })
    return pd.DataFrame(rows)


def _risk_label(billed_amount, length_of_stay, prior_claims_count, provider_risk_baseline, rng):
    score = (
        0.00015 * billed_amount
        + 0.08 * length_of_stay
        + 0.05 * prior_claims_count
        + 3.0 * provider_risk_baseline
        + rng.normal(0, 0.6)
    )
    if score < 1.2:
        return "Low"
    if score < 2.5:
        return "Medium"
    return "High"


def generate_claims(rng: np.random.Generator, providers: pd.DataFrame, patients: pd.DataFrame) -> pd.DataFrame:
    provider_ids = providers["provider_id"].to_numpy()
    provider_risk = dict(zip(providers["provider_id"], providers["risk_baseline"]))
    provider_avg = dict(zip(providers["provider_id"], providers["avg_claim_amount"]))
    patient_ids = patients["patient_id"].to_numpy()

    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=TIMESERIES_DAYS)

    rows = []
    for i in range(N_CLAIMS):
        provider_id = rng.choice(provider_ids)
        patient_id = rng.choice(patient_ids)
        treatment_type = rng.choice(TREATMENT_TYPES)
        base_amount = provider_avg[provider_id]
        billed_amount = max(50.0, round(rng.normal(base_amount, base_amount * 0.35), 2))
        length_of_stay = int(max(0, rng.poisson(2 if treatment_type == "Inpatient" else 0.3)))
        prior_claims_count = int(rng.poisson(1.5))
        risk_label = _risk_label(
            billed_amount, length_of_stay, prior_claims_count, provider_risk[provider_id], rng
        )
        denial_chance = 0.05 + provider_risk[provider_id] * 0.3
        status = "Denied" if rng.random() < denial_chance else rng.choice(["Paid", "Pending"], p=[0.85, 0.15])
        paid_amount = 0.0 if status == "Denied" else round(billed_amount * rng.uniform(0.6, 1.0), 2)

        rows.append({
            "claim_id": f"CLM{i:05d}",
            "provider_id": provider_id,
            "patient_id": patient_id,
            "procedure_code": rng.choice(PROCEDURE_CODES),
            "diagnosis_code": rng.choice(DIAGNOSIS_CODES),
            "treatment_type": treatment_type,
            "billed_amount": billed_amount,
            "paid_amount": paid_amount,
            "claim_date": str(dates[rng.integers(0, len(dates))].date()),
            "length_of_stay": length_of_stay,
            "prior_claims_count": prior_claims_count,
            "status": status,
            "risk_label": risk_label,
        })
    return pd.DataFrame(rows)


def generate_timeseries(rng: np.random.Generator, providers: pd.DataFrame) -> pd.DataFrame:
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=TIMESERIES_DAYS)
    rows = []
    for provider_id in providers["provider_id"]:
        base_count = rng.integers(3, 15)
        base_amount = rng.uniform(500, 5000)
        anomaly_days = rng.choice(len(dates), size=max(1, int(len(dates) * 0.05)), replace=False)
        for day_idx, date in enumerate(dates):
            count = max(0, int(rng.normal(base_count, base_count * 0.2)))
            amount = max(0.0, rng.normal(base_amount, base_amount * 0.2))
            if day_idx in anomaly_days:
                spike = rng.choice([2.5, 3.0, 0.15])
                count = max(0, int(count * spike))
                amount = max(0.0, amount * spike)
            rows.append({
                "provider_id": provider_id,
                "date": str(date.date()),
                "daily_claim_count": count,
                "daily_paid_total": round(amount, 2),
            })
    return pd.DataFrame(rows)


def main():
    rng = np.random.default_rng(SEED)
    Faker.seed(SEED)
    fake = Faker()

    os.makedirs(OUT_DIR, exist_ok=True)

    providers = generate_providers(rng, fake)
    patients = generate_patients(rng, fake)
    claims = generate_claims(rng, providers, patients)
    timeseries = generate_timeseries(rng, providers)

    providers.to_csv(os.path.join(OUT_DIR, "providers.csv"), index=False)
    patients.to_csv(os.path.join(OUT_DIR, "patients.csv"), index=False)
    claims.to_csv(os.path.join(OUT_DIR, "claims.csv"), index=False)
    timeseries.to_csv(os.path.join(OUT_DIR, "provider_timeseries.csv"), index=False)

    print(f"Generated {len(providers)} providers, {len(patients)} patients, "
          f"{len(claims)} claims, {len(timeseries)} timeseries rows -> {OUT_DIR}")


if __name__ == "__main__":
    main()
