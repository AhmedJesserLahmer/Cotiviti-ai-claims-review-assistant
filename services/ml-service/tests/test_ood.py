import pandas as pd

from ml import ood

PROFILE = ood.build_profile(pd.DataFrame({
    "billed_amount": [100.0, 500.0, 1000.0], "length_of_stay": [0, 2, 4], "prior_claims_count": [0, 1, 3],
    "age": [20, 40, 80], "provider_avg_claim_amount": [300.0, 600.0, 900.0],
    "treatment_type": ["Inpatient", "Outpatient", "Inpatient"], "procedure_code": ["CPT1", "CPT2", "CPT1"],
}))


def test_values_within_slack_pass():
    assert ood.check({"billed_amount": 1100.0, "treatment_type": "Inpatient", "age": 85}, PROFILE) == []


def test_flags_numeric_and_categorical_outliers():
    flags = ood.check({"billed_amount": 5000.0, "length_of_stay": 40, "procedure_code": "CPT999"}, PROFILE)
    assert len(flags) == 3 and "unknown procedure_code 'CPT999'" in flags


def test_missing_profile_disables_checks():
    assert ood.check({"billed_amount": 1e9}, None) == []
