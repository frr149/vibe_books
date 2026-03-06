from __future__ import annotations

from pydantic import ValidationError
from pytest import raises

from api.schemas import Author, BookDetail, BookListItem, Genre, Language


def test_author_genre_language_models() -> None:
    author = Author(id=10, nombre="Francois Chollet", slug="francois-chollet", book_count=3)
    genre = Genre(id=7, nombre="Programacion", slug="programacion", book_count=20)
    language = Language(id=1, code="en", nombre="ingles")

    assert author.id == 10
    assert author.slug == "francois-chollet"
    assert genre.nombre == "Programacion"
    assert language.code == "en"


def test_book_list_item_requires_core_fields() -> None:
    with raises(ValidationError):
        BookListItem.model_validate({"id": 1})

    row = BookListItem(
        id=1,
        titulo="Deep Learning with Python",
        editorial="Manning",
        idioma="ingles",
        isbn_13="9781617296864",
        isbn_10=None,
        cover_url=None,
    )
    assert row.titulo == "Deep Learning with Python"


def test_book_detail_supports_nested_taxonomies() -> None:
    detail = BookDetail(
        id=1,
        titulo="Deep Learning with Python",
        editorial="Manning",
        idioma="ingles",
        isbn_13="9781617296864",
        isbn_10="1617296864",
        cover_url="https://example.test/book.jpg",
        cover_local_path="data/covers/1_9781617296864.jpg",
        authors=[
            Author(id=10, nombre="Francois Chollet", slug="francois-chollet", book_count=3),
        ],
        genres=[
            Genre(id=7, nombre="Programacion", slug="programacion", book_count=20),
            Genre(id=8, nombre="Machine Learning / AI", slug="machine-learning-ai", book_count=15),
        ],
        language=Language(id=1, code="en", nombre="ingles"),
    )

    assert detail.language.code == "en"
    assert len(detail.authors) == 1
    assert len(detail.genres) == 2
