from __future__ import annotations

from typing import Any, cast

from fastapi.testclient import TestClient

from api.main import app


def test_openapi_includes_mvp_paths() -> None:
    client = TestClient(app)
    response = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    payload_dict = cast(dict[str, Any], payload)
    paths_raw = payload_dict.get("paths", {})
    paths = cast(dict[str, Any], paths_raw)
    assert isinstance(paths, dict)

    expected_paths = {
        "/api/v1/health",
        "/api/v1/books",
        "/api/v1/books/{book_id}",
        "/api/v1/authors",
        "/api/v1/genres",
        "/api/v1/languages",
    }
    assert expected_paths.issubset(set(paths.keys()))


def test_docs_endpoint_is_available() -> None:
    client = TestClient(app)
    response = client.get("/docs")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
