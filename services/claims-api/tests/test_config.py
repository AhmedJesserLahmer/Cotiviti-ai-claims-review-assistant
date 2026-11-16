import pytest

from core.config import Settings


def test_cors_origins_parsed_and_normalized(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://claims.example.com/, http://localhost:3000")
    assert Settings(_env_file=None).cors_origin_list == ["https://claims.example.com", "http://localhost:3000"]


def test_wildcard_origin_is_rejected(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(ValueError):
        Settings(_env_file=None).cors_origin_list
