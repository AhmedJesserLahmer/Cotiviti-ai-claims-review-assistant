"""Out-of-distribution checks against the training feature profile.

Tree models extrapolate badly and OneHotEncoder(handle_unknown="ignore") silently
zeroes unseen categories, so a claim unlike the training data still gets a confident-
looking prediction. These checks make that visible: the scoring response lists
``ood_flags`` and the agent's policy guardrail refuses to auto-approve such claims.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

NUMERIC_FEATURES = ("billed_amount", "length_of_stay", "prior_claims_count", "age", "provider_avg_claim_amount")
CATEGORICAL_FEATURES = ("treatment_type", "procedure_code")
# Allow some slack beyond the observed range before flagging.
RANGE_SLACK = 0.25


def build_profile(df: pd.DataFrame) -> dict[str, Any]:
    numeric = {}
    for name in NUMERIC_FEATURES:
        column = df[name].astype(float)
        numeric[name] = {
            "min": float(column.min()), "max": float(column.max()),
            "p01": float(column.quantile(0.01)), "p99": float(column.quantile(0.99)),
        }
    categorical = {name: sorted(df[name].astype(str).unique().tolist()) for name in CATEGORICAL_FEATURES}
    return {"numeric": numeric, "categorical": categorical}


def check(features: dict[str, Any], profile: dict[str, Any] | None) -> list[str]:
    if not profile:
        return []
    flags: list[str] = []
    for name, stats in profile.get("numeric", {}).items():
        if name not in features or features[name] is None:
            continue
        value = float(features[name])
        span = max(stats["max"] - stats["min"], 1e-9)
        low, high = stats["min"] - RANGE_SLACK * span, stats["max"] + RANGE_SLACK * span
        if value < low:
            flags.append(f"{name}={value:g} below training range [{stats['min']:g}, {stats['max']:g}]")
        elif value > high:
            flags.append(f"{name}={value:g} above training range [{stats['min']:g}, {stats['max']:g}]")
    for name, known in profile.get("categorical", {}).items():
        value = features.get(name)
        if value is not None and str(value) not in known:
            flags.append(f"unknown {name} '{str(value)[:40]}'")
    return flags
