from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from api.main import app


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


def test_books_list_returns_paginated_payload(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    db_path = tmp_path / "books_catalog.db"
    _prepare_catalog_db(db_path)
    monkeypatch.setattr("api.main.DB_PATH", db_path)

    client = TestClient(app)
    response = client.get("/api/v1/books?page=1&page_size=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"] == {
        "page": 1,
        "page_size": 1,
        "total": 2,
        "total_pages": 2,
    }
    assert len(payload["items"]) == 1
    assert payload["items"][0]["id"] == 1


def test_books_list_supports_readable_filters(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    db_path = tmp_path / "books_catalog.db"
    _prepare_catalog_db(db_path)
    monkeypatch.setattr("api.main.DB_PATH", db_path)

    client = TestClient(app)
    response = client.get("/api/v1/books?author=Francois%20Chollet&genre=Programacion")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total"] == 1
    assert payload["items"][0]["titulo"] == "Deep Learning with Python"


def test_books_list_returns_contract_error_on_ambiguous_filters(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    db_path = tmp_path / "books_catalog.db"
    _prepare_catalog_db(db_path)
    monkeypatch.setattr("api.main.DB_PATH", db_path)

    client = TestClient(app)
    response = client.get("/api/v1/books?author=Francois%20Chollet&author_id=10")

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "invalid_query"
