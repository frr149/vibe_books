from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from api.main import app


def test_health_returns_ok_when_db_exists(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    db_path = tmp_path / "books_catalog.db"
    db_path.touch()
    monkeypatch.setattr("api.main.DB_PATH", db_path)

    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_returns_503_when_db_is_missing(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    db_path = tmp_path / "missing.db"
    monkeypatch.setattr("api.main.DB_PATH", db_path)

    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "database_not_found"}
