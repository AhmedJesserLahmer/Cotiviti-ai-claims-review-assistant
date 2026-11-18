"""Versioned model registry on the local filesystem.

Layout::

    ml/models/
        CURRENT                 -> text file with the active version id
        <version>/
            manifest.json       -> metrics, data hash, features, created_at
            classifier.joblib
            predictor.joblib
            cluster_model.joblib
            anomaly_model.joblib

Every training run creates a new immutable version directory and then moves the
CURRENT pointer, so a bad model is rolled back by pointing CURRENT (or the
``MODEL_VERSION`` environment variable) at the previous version. In Kubernetes the
directory lives on a volume shared by the training CronJob and the service.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib

MODELS_ROOT = Path(os.environ.get("MODELS_DIR", Path(__file__).parent / "models"))
CURRENT_FILE = "CURRENT"
MANIFEST_FILE = "manifest.json"
ARTIFACTS = ("classifier", "predictor", "cluster_model", "anomaly_model")


class ModelNotFoundError(RuntimeError):
    pass


def new_version_id(now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    return "v" + now.strftime("%Y%m%dT%H%M%SZ")


def version_dir(version: str, root: Path = MODELS_ROOT) -> Path:
    if not version or "/" in version or version.startswith("."):
        raise ValueError(f"invalid model version {version!r}")
    return root / version


def save_version(
    version: str,
    artifacts: dict[str, Any],
    manifest: dict[str, Any],
    *,
    root: Path = MODELS_ROOT,
    activate: bool = True,
) -> Path:
    target = version_dir(version, root)
    if target.exists():
        raise FileExistsError(f"model version {version} already exists (versions are immutable)")
    target.mkdir(parents=True)
    for name, obj in artifacts.items():
        joblib.dump(obj, target / f"{name}.joblib")
    full_manifest = {"version": version, "created_at": datetime.now(UTC).isoformat(), **manifest}
    (target / MANIFEST_FILE).write_text(json.dumps(full_manifest, indent=2, default=str))
    if activate:
        set_current(version, root=root)
    return target


def set_current(version: str, *, root: Path = MODELS_ROOT) -> None:
    if not (version_dir(version, root) / MANIFEST_FILE).exists():
        raise ModelNotFoundError(f"model version {version} not found")
    tmp = root / f".{CURRENT_FILE}.tmp"
    tmp.write_text(version)
    tmp.replace(root / CURRENT_FILE)  # atomic on POSIX


def current_version(*, root: Path = MODELS_ROOT) -> str:
    pinned = os.environ.get("MODEL_VERSION")
    if pinned:
        return pinned
    pointer = root / CURRENT_FILE
    if not pointer.exists():
        raise ModelNotFoundError(f"no active model in {root} (run: python -m ml.train_models)")
    return pointer.read_text().strip()


def list_versions(*, root: Path = MODELS_ROOT) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    try:
        active = current_version(root=root)
    except ModelNotFoundError:
        active = None
    versions = []
    for manifest_path in sorted(root.glob(f"*/{MANIFEST_FILE}"), reverse=True):
        manifest = json.loads(manifest_path.read_text())
        manifest["active"] = manifest.get("version") == active
        versions.append(manifest)
    return versions


@dataclass(frozen=True)
class ModelBundle:
    version: str
    manifest: dict[str, Any]
    classifier: Any
    predictor: Any


def load_bundle(version: str | None = None, *, root: Path = MODELS_ROOT) -> ModelBundle:
    version = version or current_version(root=root)
    path = version_dir(version, root)
    manifest_path = path / MANIFEST_FILE
    if not manifest_path.exists():
        raise ModelNotFoundError(f"model version {version} not found in {root}")
    return ModelBundle(
        version=version,
        manifest=json.loads(manifest_path.read_text()),
        classifier=joblib.load(path / "classifier.joblib"),
        predictor=joblib.load(path / "predictor.joblib"),
    )
