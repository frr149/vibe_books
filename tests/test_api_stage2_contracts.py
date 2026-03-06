from __future__ import annotations

from pytest import raises

from api.contracts import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    build_error_payload,
    compute_pagination,
)


def test_pagination_defaults_and_offsets() -> None:
    page = compute_pagination()
    assert page.page == DEFAULT_PAGE
    assert page.page_size == DEFAULT_PAGE_SIZE
    assert page.offset == 0
    assert page.limit == DEFAULT_PAGE_SIZE

    second_page = compute_pagination(page=2, page_size=25)
    assert second_page.offset == 25
    assert second_page.limit == 25


def test_pagination_enforces_bounds() -> None:
    capped = compute_pagination(page=1, page_size=MAX_PAGE_SIZE + 500)
    assert capped.page_size == MAX_PAGE_SIZE

    with raises(ValueError):
        compute_pagination(page=0, page_size=20)

    with raises(ValueError):
        compute_pagination(page=1, page_size=0)


def test_error_payload_contract() -> None:
    payload = build_error_payload(code="invalid_query", message="Parametro invalido")
    assert payload == {"error": {"code": "invalid_query", "message": "Parametro invalido"}}

    payload_with_details = build_error_payload(
        code="invalid_query",
        message="Parametro invalido",
        details={"field": "page_size"},
    )
    assert payload_with_details["error"]["code"] == "invalid_query"
    assert payload_with_details["error"]["details"] == {"field": "page_size"}
