from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class Pagination:
    page: int
    page_size: int
    offset: int
    limit: int


def compute_pagination(
    page: int | None = None,
    page_size: int | None = None,
) -> Pagination:
    resolved_page = DEFAULT_PAGE if page is None else page
    resolved_page_size = DEFAULT_PAGE_SIZE if page_size is None else page_size

    if resolved_page < 1:
        raise ValueError("page debe ser >= 1")
    if resolved_page_size < 1:
        raise ValueError("page_size debe ser >= 1")

    bounded_page_size = min(resolved_page_size, MAX_PAGE_SIZE)
    offset = (resolved_page - 1) * bounded_page_size
    return Pagination(
        page=resolved_page,
        page_size=bounded_page_size,
        offset=offset,
        limit=bounded_page_size,
    )


def build_error_payload(
    code: str,
    message: str,
    *,
    details: Mapping[str, object] | None = None,
) -> dict[str, dict[str, object]]:
    body: dict[str, object] = {
        "code": code,
        "message": message,
    }
    if details is not None:
        body["details"] = dict(details)
    return {"error": body}
