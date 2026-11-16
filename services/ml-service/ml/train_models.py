"""Trains all ML models used by the Claims Review Assistant POC:
  - Classification: RandomForestClassifier -> claim risk_label
  - Prediction: GradientBoostingRegressor -> predicted paid_amount
  - Clustering: KMeans(k=4) -> provider behavior cluster
  - Anomaly Detection: IsolationForest -> anomalous provider billing days

Run with: python -m ml.train_models
Reads CSVs from data/, writes a new immutable model version to the registry
(ml/models/<version>/, see ml/registry.py) with holdout metrics, and writes
augmented providers.csv / provider_timeseries.csv back to data/
with cluster and anomaly columns so they can be seeded into MongoDB as-is.
"""

import hashlib
import os

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, IsolationForest, RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml import registry

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
HOLDOUT_FRACTION = 0.2
RANDOM_STATE = 42

# One distinct label per cost-rank tier (index 0 = cheapest cluster ... index 3 =
# priciest). Kept fully separate from OUTLIER_LABEL below so the two labeling rules
# in train_clustering() can never collide: previously, index 3 doubled as both "the
# priciest cluster's cost-tier name" AND the outlier placeholder, so if the actual
# highest-denial cluster wasn't also the priciest one, two different clusters ended
# up sharing the "High-Risk / High-Denial Outlier" label while "Standard Volume Care"
# went unused by any cluster.
COST_TIER_LABELS = [
    "Low-Cost Routine Care",
    "Standard Volume Care",
    "High-Cost Complex Care",
    "Premium / High-Cost Care",
]
OUTLIER_LABEL = "High-Risk / High-Denial Outlier"


def load_data():
    providers = pd.read_csv(os.path.join(DATA_DIR, "providers.csv"))
    patients = pd.read_csv(os.path.join(DATA_DIR, "patients.csv"))
    claims = pd.read_csv(os.path.join(DATA_DIR, "claims.csv"))
    timeseries = pd.read_csv(os.path.join(DATA_DIR, "provider_timeseries.csv"))
    return providers, patients, claims, timeseries


def build_training_frame(claims, patients, providers):
    df = claims.merge(patients, on="patient_id", how="left")
    df = df.merge(
        providers[["provider_id", "avg_claim_amount"]].rename(
            columns={"avg_claim_amount": "provider_avg_claim_amount"}
        ),
        on="provider_id",
        how="left",
    )
    return df


def train_classifier(df: pd.DataFrame):
    features_num = ["billed_amount", "length_of_stay", "prior_claims_count", "age"]
    features_cat = ["treatment_type", "procedure_code"]

    X = df[features_num + features_cat]
    y = df["risk_label"]

    preprocessor = ColumnTransformer([
        ("num", "passthrough", features_num),
        ("cat", OneHotEncoder(handle_unknown="ignore"), features_cat),
    ])
    pipeline = Pipeline([
        ("preprocess", preprocessor),
        ("model", RandomForestClassifier(n_estimators=200, max_depth=8, random_state=42)),
    ])
    pipeline.fit(X, y)
    pipeline.feature_columns_ = features_num + features_cat
    return pipeline


def train_predictor(df: pd.DataFrame):
    features_num = ["billed_amount", "length_of_stay", "provider_avg_claim_amount"]
    features_cat = ["treatment_type"]

    X = df[features_num + features_cat]
    y = df["paid_amount"]

    preprocessor = ColumnTransformer([
        ("num", "passthrough", features_num),
        ("cat", OneHotEncoder(handle_unknown="ignore"), features_cat),
    ])
    pipeline = Pipeline([
        ("preprocess", preprocessor),
        ("model", GradientBoostingRegressor(n_estimators=150, max_depth=3, random_state=42)),
    ])
    pipeline.fit(X, y)
    pipeline.feature_columns_ = features_num + features_cat
    return pipeline


def train_clustering(claims: pd.DataFrame, providers: pd.DataFrame):
    agg = claims.groupby("provider_id").agg(
        avg_billed=("billed_amount", "mean"),
        claim_volume=("claim_id", "count"),
        denial_rate=("status", lambda s: (s == "Denied").mean()),
        avg_length_of_stay=("length_of_stay", "mean"),
    ).reset_index()

    feature_cols = ["avg_billed", "claim_volume", "denial_rate", "avg_length_of_stay"]
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(agg[feature_cols])

    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    agg["cluster_id"] = kmeans.fit_predict(X_scaled)

    # Rank clusters by avg_billed so cost-tier labels are meaningful, then
    # independently overwrite whichever cluster has the highest denial rate with the
    # outlier label. Because COST_TIER_LABELS and OUTLIER_LABEL never share a value,
    # this is a clean overwrite: exactly one cluster ever ends up "Outlier", and the
    # cost-tier label it displaced simply isn't used by any cluster that round
    # (expected — there are 4 clusters but 5 possible label meanings).
    centroid_order = agg.groupby("cluster_id")["avg_billed"].mean().sort_values().index.tolist()
    label_by_cluster = {cid: COST_TIER_LABELS[i] for i, cid in enumerate(centroid_order)}

    highest_denial_cluster = agg.groupby("cluster_id")["denial_rate"].mean().idxmax()
    label_by_cluster[highest_denial_cluster] = OUTLIER_LABEL

    agg["cluster_label"] = agg["cluster_id"].map(label_by_cluster)

    # Drop columns from a previous training run so retraining is idempotent
    # (otherwise every run adds _x/_y duplicates to providers.csv).
    derived = [c for c in providers.columns if c in agg.columns and c != "provider_id"]
    providers_out = providers.drop(columns=derived).merge(agg, on="provider_id", how="left")
    return providers_out, scaler, kmeans, feature_cols, label_by_cluster


DERIVED_TIMESERIES_COLUMNS = ["anomaly_score", "is_anomaly"]


def train_anomaly_detector(timeseries: pd.DataFrame):
    ts = timeseries.drop(columns=DERIVED_TIMESERIES_COLUMNS, errors="ignore")
    ts = ts.sort_values(["provider_id", "date"]).reset_index(drop=True)

    def rolling_z(column: str) -> pd.Series:
        # groupby().transform keeps the original index and columns (provider_id
        # included). groupby().apply drops the grouping column on pandas >= 3,
        # which silently produced a time-series file without provider_id.
        grouped = ts.groupby("provider_id")[column]
        mean = grouped.transform(lambda s: s.rolling(7, min_periods=2).mean())
        std = grouped.transform(lambda s: s.rolling(7, min_periods=2).std()).replace(0, np.nan)
        return ((ts[column] - mean) / std).fillna(0)

    ts["count_z"] = rolling_z("daily_claim_count")
    ts["amount_z"] = rolling_z("daily_paid_total")

    features = ts[["count_z", "amount_z"]]
    model = IsolationForest(contamination=0.05, random_state=42)
    model.fit(features)

    ts["anomaly_score"] = -model.score_samples(features)  # higher = more anomalous
    ts["is_anomaly"] = model.predict(features) == -1

    return ts, model


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluate_claim_models(df: pd.DataFrame) -> dict:
    """Holdout metrics: fit on 80%, score on 20%. Deployed models are refit on all rows."""
    train, test = train_test_split(
        df, test_size=HOLDOUT_FRACTION, random_state=RANDOM_STATE, stratify=df["risk_label"]
    )
    classifier = train_classifier(train)
    predictor = train_predictor(train)
    predicted_labels = classifier.predict(test[classifier.feature_columns_])
    predicted_paid = predictor.predict(test[predictor.feature_columns_])
    return {
        "holdout_rows": int(len(test)),
        "classifier": {
            "accuracy": round(float(accuracy_score(test["risk_label"], predicted_labels)), 4),
            "macro_f1": round(float(f1_score(test["risk_label"], predicted_labels, average="macro")), 4),
        },
        "predictor": {
            "mae": round(float(mean_absolute_error(test["paid_amount"], predicted_paid)), 2),
            "r2": round(float(r2_score(test["paid_amount"], predicted_paid)), 4),
        },
    }


def main():
    providers, patients, claims, timeseries = load_data()
    training_frame = build_training_frame(claims, patients, providers)

    metrics = evaluate_claim_models(training_frame)
    classifier = train_classifier(training_frame)
    predictor = train_predictor(training_frame)

    providers_out, scaler, kmeans, cluster_features, label_by_cluster = train_clustering(claims, providers)
    providers_out.to_csv(os.path.join(DATA_DIR, "providers.csv"), index=False)

    ts_out, anomaly_model = train_anomaly_detector(timeseries)
    ts_out.drop(columns=["count_z", "amount_z"]).to_csv(
        os.path.join(DATA_DIR, "provider_timeseries.csv"), index=False
    )

    version = os.environ.get("NEW_MODEL_VERSION") or registry.new_version_id()
    manifest = {
        "training_rows": int(len(training_frame)),
        "data_sha256": {"claims.csv": _sha256(os.path.join(DATA_DIR, "claims.csv"))},
        "features": {"classifier": classifier.feature_columns_, "predictor": predictor.feature_columns_},
        "metrics": metrics,
        "clusters": {str(k): v for k, v in label_by_cluster.items()},
    }
    path = registry.save_version(
        version,
        {
            "classifier": classifier,
            "predictor": predictor,
            "cluster_model": {
                "scaler": scaler, "kmeans": kmeans, "features": cluster_features, "labels": label_by_cluster,
            },
            "anomaly_model": anomaly_model,
        },
        manifest,
    )

    print(f"Trained model version {version} -> {path}")
    print(f"Holdout metrics: {metrics}")
    print(f"Augmented providers.csv with cluster_id/cluster_label ({len(providers_out)} rows)")
    print(f"Augmented provider_timeseries.csv with anomaly_score/is_anomaly ({len(ts_out)} rows)")


if __name__ == "__main__":
    main()
