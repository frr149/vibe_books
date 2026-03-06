from __future__ import annotations

from pytest import raises

from api.filters import BookFilters, build_book_filters


def test_build_book_filters_accepts_readable_filters() -> None:
    filters = build_book_filters(
        q="deep learning",
        language="en",
        author="Francois Chollet",
        genre="Machine Learning / AI",
        has_isbn=True,
    )
    assert isinstance(filters, BookFilters)
    assert filters.author == "Francois Chollet"
    assert filters.genre == "Machine Learning / AI"
    assert filters.has_isbn is True


def test_build_book_filters_accepts_identifier_filters() -> None:
    filters = build_book_filters(
        author_id=10,
        genre_id=4,
    )
    assert filters.author_id == 10
    assert filters.genre_id == 4


def test_build_book_filters_rejects_ambiguous_author_inputs() -> None:
    with raises(ValueError):
        build_book_filters(author="Francois Chollet", author_id=10)


def test_build_book_filters_rejects_ambiguous_genre_inputs() -> None:
    with raises(ValueError):
        build_book_filters(genre="Programacion", genre_id=2)
