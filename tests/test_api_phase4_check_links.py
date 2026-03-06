from __future__ import annotations

from scripts.api_check_links import EndpointResult, check_endpoints, has_failures


def test_check_endpoints_marks_success_and_failure() -> None:
    status_by_url = {
        "http://127.0.0.1:8000/api/v1/health": 200,
        "http://127.0.0.1:8000/openapi.json": 200,
        "http://127.0.0.1:8000/docs": 500,
    }

    def fake_get_status(url: str, timeout_seconds: float) -> int:
        assert timeout_seconds == 2.0
        return status_by_url[url]

    results = check_endpoints(
        base_url="http://127.0.0.1:8000",
        paths=["/api/v1/health", "/openapi.json", "/docs"],
        timeout_seconds=2.0,
        get_status=fake_get_status,
    )

    assert results == [
        EndpointResult(path="/api/v1/health", status_code=200, ok=True),
        EndpointResult(path="/openapi.json", status_code=200, ok=True),
        EndpointResult(path="/docs", status_code=500, ok=False),
    ]
    assert has_failures(results) is True


def test_check_endpoints_marks_request_error() -> None:
    def fake_get_status(url: str, timeout_seconds: float) -> int:
        raise OSError("network_down")

    results = check_endpoints(
        base_url="http://127.0.0.1:8000",
        paths=["/api/v1/health"],
        timeout_seconds=2.0,
        get_status=fake_get_status,
    )

    assert results == [
        EndpointResult(path="/api/v1/health", status_code=0, ok=False),
    ]
    assert has_failures(results) is True
