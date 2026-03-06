from __future__ import annotations

from dataclasses import dataclass

from etl.normalize import normalize_display_text


@dataclass(frozen=True)
class BookFilters:
    q: str | None
    language: str | None
    author: str | None
    author_id: int | None
    genre: str | None
    genre_id: int | None
    has_isbn: bool | None


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = normalize_display_text(value).strip()
    return cleaned or None


def build_book_filters(
    *,
    q: str | None = None,
    language: str | None = None,
    author: str | None = None,
    author_id: int | None = None,
    genre: str | None = None,
    genre_id: int | None = None,
    has_isbn: bool | None = None,
) -> BookFilters:
    clean_author = _clean_text(author)
    clean_genre = _clean_text(genre)

    if clean_author is not None and author_id is not None:
        raise ValueError("No se puede enviar author y author_id a la vez")
    if clean_genre is not None and genre_id is not None:
        raise ValueError("No se puede enviar genre y genre_id a la vez")

    return BookFilters(
        q=_clean_text(q),
        language=_clean_text(language),
        author=clean_author,
        author_id=author_id,
        genre=clean_genre,
        genre_id=genre_id,
        has_isbn=has_isbn,
    )
