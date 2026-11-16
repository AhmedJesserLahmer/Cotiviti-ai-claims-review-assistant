import pytest

from ml import registry


def test_save_activate_list_and_load(tmp_path, monkeypatch):
    monkeypatch.delenv("MODEL_VERSION", raising=False)
    registry.save_version("v1", {"classifier": {"m": 1}, "predictor": {"m": 2}}, {"metrics": {"a": 1}}, root=tmp_path)
    registry.save_version("v2", {"classifier": {"m": 3}, "predictor": {"m": 4}}, {}, root=tmp_path)
    assert registry.current_version(root=tmp_path) == "v2"
    registry.set_current("v1", root=tmp_path)  # rollback
    bundle = registry.load_bundle(root=tmp_path)
    assert bundle.version == "v1" and bundle.classifier == {"m": 1} and bundle.manifest["metrics"] == {"a": 1}
    versions = registry.list_versions(root=tmp_path)
    assert [v["version"] for v in versions] == ["v2", "v1"] and versions[1]["active"]


def test_versions_are_immutable_and_validated(tmp_path):
    registry.save_version("v1", {}, {}, root=tmp_path)
    with pytest.raises(FileExistsError):
        registry.save_version("v1", {}, {}, root=tmp_path)
    with pytest.raises(ValueError):
        registry.version_dir("../etc")
    with pytest.raises(registry.ModelNotFoundError):
        registry.set_current("missing", root=tmp_path)


def test_env_pin_and_missing_registry(tmp_path, monkeypatch):
    with pytest.raises(registry.ModelNotFoundError):
        registry.current_version(root=tmp_path)
    monkeypatch.setenv("MODEL_VERSION", "v9")
    assert registry.current_version(root=tmp_path) == "v9"


def test_version_ids_are_sortable():
    from datetime import datetime, timezone

    assert registry.new_version_id(datetime(2026, 11, 17, 9, 5, tzinfo=timezone.utc)) == "v20261117T090500Z"
