from __future__ import annotations

import sqlite3
from pathlib import Path

from api.contracts import compute_pagination
from api.filters import build_book_filters
from api.repository import CatalogRepository


def _prepare_catalog_db(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE languages (
              id INTEGER PRIMARY KEY,
              code TEXT NOT NULL UNIQUE,
              nombre TEXT NOT NULL UNIQUE,
              nombre_norm TEXT NOT NULL UNIQUE
            ) STRICT;
            CREATE TABLE books (
              id INTEGER PRIMARY KEY,
              titulo TEXT NOT NULL,
              editorial TEXT,
              language_id INTEGER NOT NULL,
              isbn_13 TEXT,
              isbn_10 TEXT,
              cover_url TEXT,
              cover_local_path TEXT,
              FOREIGN KEY (language_id) REFERENCES languages(id) ON DELETE RESTRICT
            ) STRICT;
            CREATE TABLE authors (
              id INTEGER PRIMARY KEY,
              nombre TEXT NOT NULL,
              nombre_norm TEXT NOT NULL UNIQUE
            ) STRICT;
            CREATE TABLE genres (
              id INTEGER PRIMARY KEY,
              nombre TEXT NOT NULL,
              nombre_norm TEXT NOT NULL UNIQUE
            ) STRICT;
            CREATE TABLE book_authors (
              book_id INTEGER NOT NULL,
              author_id INTEGER NOT NULL,
              author_order INTEGER NOT NULL DEFAULT 1,
              PRIMARY KEY (book_id, author_id),
              FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
              FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE RESTRICT
            ) STRICT;
            CREATE TABLE book_genres (
              book_id INTEGER NOT NULL,
              genre_id INTEGER NOT NULL,
              PRIMARY KEY (book_id, genre_id),
              FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
              FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE RESTRICT
            ) STRICT;
            """
        )

        connection.executemany(
            "INSERT INTO languages (id, code, nombre, nombre_norm) VALUES (?, ?, ?, ?)",
            [
                (1, "en", "ingles", "ingles"),
                (2, "fr", "frances", "frances"),
            ],
        )
        connection.executemany(
            """
            INSERT INTO books (id, titulo, editorial, language_id, isbn_13, isbn_10, cover_url, cover_local_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1, "Deep Learning with Python", "Manning", 1, "9781617296864", "1617296864", None, None),
                (2, "Le Petit Prince", "Gallimard", 2, None, None, None, None),
            ],
        )
        connection.executemany(
            "INSERT INTO authors (id, nombre, nombre_norm) VALUES (?, ?, ?)",
            [
                (10, "Francois Chollet", "francois chollet"),
                (11, "Antoine de Saint-Exupery", "antoine de saint exupery"),
            ],
        )
        connection.executemany(
            "INSERT INTO genres (id, nombre, nombre_norm) VALUES (?, ?, ?)",
            [
                (7, "Programacion", "programacion"),
                (8, "Ficcion", "ficcion"),
            ],
        )
        connection.executemany(
            "INSERT INTO book_authors (book_id, author_id, author_order) VALUES (?, ?, ?)",
            [
                (1, 10, 1),
                (2, 11, 1),
            ],
        )
        connection.executemany(
            "INSERT INTO book_genres (book_id, genre_id) VALUES (?, ?)",
            [
                (1, 7),
                (2, 8),
            ],
        )
        connection.commit()
    finally:
        connection.close()


def test_repository_lists_books_with_readable_filters(tmp_path: Path) -> None:
    db_path = tmp_path / "catalog.db"
    _prepare_catalog_db(db_path)
    repository = CatalogRepository(db_path)

    filters = build_book_filters(author="Francois Chollet", genre="Programacion")
    pagination = compute_pagination(page=1, page_size=20)
    items, total = repository.list_books(filters=filters, pagination=pagination)

    assert total == 1
    assert len(items) == 1
    assert items[0].id == 1
    assert items[0].titulo == "Deep Learning with Python"


def test_repository_supports_identifier_filters_and_blocks_sql_injection(tmp_path: Path) -> None:
    db_path = tmp_path / "catalog.db"
    _prepare_catalog_db(db_path)
    repository = CatalogRepository(db_path)

    filters_by_id = build_book_filters(author_id=11)
    items, total = repository.list_books(filters=filters_by_id, pagination=compute_pagination())
    assert total == 1
    assert items[0].id == 2

    injected = build_book_filters(author="Francois Chollet' OR 1=1 --")
    injected_items, injected_total = repository.list_books(filters=injected, pagination=compute_pagination())
    assert injected_total == 0
    assert injected_items == []


def test_repository_returns_book_detail_with_relations(tmp_path: Path) -> None:
    db_path = tmp_path / "catalog.db"
    _prepare_catalog_db(db_path)
    repository = CatalogRepository(db_path)

    detail = repository.get_book_detail(book_id=1)
    assert detail is not None
    assert detail.id == 1
    assert detail.language.code == "en"
    assert len(detail.authors) == 1
    assert detail.authors[0].nombre == "Francois Chollet"
    assert len(detail.genres) == 1
    assert detail.genres[0].nombre == "Programacion"
