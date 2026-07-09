"""Trains all ML models used by the Claims Review Assistant POC:
  - Classification: RandomForestClassifier -> claim risk_label
  - Prediction: GradientBoostingRegressor -> predicted paid_amount
  - Clustering: KMeans(k=4) -> provider behavior cluster
  - Anomaly Detection: IsolationForest -> anomalous provider billing days

Run with: python -m ml.train_models
Reads CSVs from backend/data/, writes models to backend/ml/models/,
and writes augmented providers.csv / provider_timeseries.csv back to backend/data/
with cluster and anomaly columns so they can be seeded into MongoDB as-is.
"""

import os

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, IsolationForest, RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

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

    providers_out = providers.merge(agg, on="provider_id", how="left")
    return providers_out, scaler, kmeans, feature_cols, label_by_cluster


def train_anomaly_detector(timeseries: pd.DataFrame):
    ts = timeseries.sort_values(["provider_id", "date"]).copy()

    def add_zscores(group: pd.DataFrame) -> pd.DataFrame:
        roll_count = group["daily_claim_count"].rolling(7, min_periods=2)
        roll_amount = group["daily_paid_total"].rolling(7, min_periods=2)
        count_mean, count_std = roll_count.mean(), roll_count.std().replace(0, np.nan)
        amount_mean, amount_std = roll_amount.mean(), roll_amount.std().replace(0, np.nan)
        group["count_z"] = ((group["daily_claim_count"] - count_mean) / count_std).fillna(0)
        group["amount_z"] = ((group["daily_paid_total"] - amount_mean) / amount_std).fillna(0)
        return group

    ts = ts.groupby("provider_id", group_keys=False).apply(add_zscores)

    features = ts[["count_z", "amount_z"]]
    model = IsolationForest(contamination=0.05, random_state=42)
    model.fit(features)

    ts["anomaly_score"] = -model.score_samples(features)  # higher = more anomalous
    ts["is_anomaly"] = model.predict(features) == -1

    return ts, model


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)
    providers, patients, claims, timeseries = load_data()

    training_frame = build_training_frame(claims, patients, providers)

    classifier = train_classifier(training_frame)
    joblib.dump(classifier, os.path.join(MODELS_DIR, "classifier.joblib"))

    predictor = train_predictor(training_frame)
    joblib.dump(predictor, os.path.join(MODELS_DIR, "predictor.joblib"))

    providers_out, scaler, kmeans, cluster_features, label_by_cluster = train_clustering(claims, providers)
    joblib.dump(
        {"scaler": scaler, "kmeans": kmeans, "features": cluster_features, "labels": label_by_cluster},
        os.path.join(MODELS_DIR, "cluster_model.joblib"),
    )
    providers_out.to_csv(os.path.join(DATA_DIR, "providers.csv"), index=False)

    ts_out, anomaly_model = train_anomaly_detector(timeseries)
    joblib.dump(anomaly_model, os.path.join(MODELS_DIR, "anomaly_model.joblib"))
    ts_out.drop(columns=["count_z", "amount_z"]).to_csv(
        os.path.join(DATA_DIR, "provider_timeseries.csv"), index=False
    )

    print("Trained and saved: classifier, predictor, cluster_model, anomaly_model")
    print(f"Augmented providers.csv with cluster_id/cluster_label ({len(providers_out)} rows)")
    print(f"Augmented provider_timeseries.csv with anomaly_score/is_anomaly ({len(ts_out)} rows)")


if __name__ == "__main__":
    main()
