from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Callable, Sequence

import httpx

DEFAULT_PATHS: tuple[str, ...] = (
    "/api/v1/health",
    "/openapi.json",
    "/docs",
    "/api/v1/books?page=1&page_size=1",
    "/api/v1/authors",
    "/api/v1/genres",
    "/api/v1/languages",
)


@dataclass(frozen=True)
class EndpointResult:
    path: str
    status_code: int
    ok: bool


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _normalize_path(path: str) -> str:
    if path.startswith("/"):
        return path
    return f"/{path}"


def _fetch_status(url: str, timeout_seconds: float) -> int:
    response = httpx.get(url, timeout=timeout_seconds, follow_redirects=True)
    return response.status_code


def check_endpoints(
    *,
    base_url: str,
    paths: Sequence[str],
    timeout_seconds: float,
    get_status: Callable[[str, float], int] = _fetch_status,
) -> list[EndpointResult]:
    resolved_base_url = _normalize_base_url(base_url)
    results: list[EndpointResult] = []

    for raw_path in paths:
        path = _normalize_path(raw_path)
        url = f"{resolved_base_url}{path}"
        try:
            status_code = get_status(url, timeout_seconds)
        except Exception:
            status_code = 0
        ok = 200 <= status_code < 400
        results.append(EndpointResult(path=path, status_code=status_code, ok=ok))
    return results


def has_failures(results: Sequence[EndpointResult]) -> bool:
    return any(not result.ok for result in results)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Valida endpoints criticos de la API local.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="URL base de la API en ejecucion (default: http://127.0.0.1:8000).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="Timeout por request en segundos (default: 2.0).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = check_endpoints(
        base_url=args.base_url,
        paths=DEFAULT_PATHS,
        timeout_seconds=args.timeout,
    )

    for result in results:
        label = "OK" if result.ok else "FAIL"
        print(f"[{label}] {result.path} -> {result.status_code}")

    if has_failures(results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
