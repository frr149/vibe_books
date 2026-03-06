from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from api.schemas import BookDetail, BookListItem

FIXTURES_DIR = Path("tests/fixtures/real")


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return cast(dict[str, Any], json.load(fh))


def test_book_detail_full_fixture_matches_schema() -> None:
    payload = _load_json(FIXTURES_DIR / "book_detail_full.json")
    model = BookDetail.model_validate(payload)
    assert set(payload.keys()) == set(BookDetail.model_fields.keys())
    assert model.id > 0


def test_book_detail_sparse_fixture_matches_schema() -> None:
    payload = _load_json(FIXTURES_DIR / "book_detail_sparse.json")
    model = BookDetail.model_validate(payload)
    assert set(payload.keys()) == set(BookDetail.model_fields.keys())
    assert model.id > 0


def test_books_list_fixture_matches_schema() -> None:
    payload = _load_json(FIXTURES_DIR / "books_list_page1.json")
    assert set(payload.keys()) == {"items", "pagination"}
    items_raw = payload["items"]
    assert isinstance(items_raw, list)
    items = cast(list[dict[str, Any]], items_raw)
    pagination_raw = payload["pagination"]
    assert isinstance(pagination_raw, dict)
    pagination = cast(dict[str, Any], pagination_raw)
    assert set(pagination.keys()) == {"page", "page_size", "total", "total_pages"}

    for item in items:
        BookListItem.model_validate(item)
        assert set(item.keys()) == set(BookListItem.model_fields.keys())
