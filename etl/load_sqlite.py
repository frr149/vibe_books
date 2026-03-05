from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from etl.normalize import UNKNOWN_VALUE, matching_key, normalize_display_text

LANGUAGE_SEED = (
    ("es", "espanol"),
    ("pt", "portugues"),
    ("en", "ingles"),
    ("fr", "frances"),
)

LANGUAGE_CODE_BY_NAME = {
    "espanol": "es",
    "portugues": "pt",
    "ingles": "en",
    "frances": "fr",
    "aleman": "de",
    "italiano": "it",
    "desconocido": "xx",
}


def _clean_isbn13(value: str) -> str | None:
    token = "".join(char for char in (value or "") if char.isdigit())
    if len(token) == 13:
        return token
    return None


def _clean_isbn10(value: str) -> str | None:
    token = "".join(char for char in (value or "") if char.isdigit() or char.upper() == "X")
    if len(token) == 10:
        return token
    return None


def _clean_text(value: str) -> str | None:
    cleaned = normalize_display_text(value).strip()
    if not cleaned:
        return None
    if matching_key(cleaned) == UNKNOWN_VALUE:
        return None
    return cleaned


def _split_values(raw_value: str) -> list[str]:
    cleaned = normalize_display_text(raw_value).strip()
    if not cleaned or matching_key(cleaned) == UNKNOWN_VALUE:
        return []
    return [item.strip() for item in cleaned.split(";") if item.strip()]


def _language_code_from_name(language_name: str) -> str:
    key = matching_key(language_name)
    if not key:
        return "xx"
    if key in LANGUAGE_CODE_BY_NAME:
        return LANGUAGE_CODE_BY_NAME[key]
    if len(key) >= 2:
        return key[:2]
    return "xx"


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS languages (
          id INTEGER PRIMARY KEY,
          code TEXT NOT NULL UNIQUE,
          nombre TEXT NOT NULL UNIQUE,
          nombre_norm TEXT NOT NULL UNIQUE
        ) STRICT;

        CREATE TABLE IF NOT EXISTS books (
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

        CREATE TABLE IF NOT EXISTS authors (
          id INTEGER PRIMARY KEY,
          nombre TEXT NOT NULL,
          nombre_norm TEXT NOT NULL UNIQUE
        ) STRICT;

        CREATE TABLE IF NOT EXISTS genres (
          id INTEGER PRIMARY KEY,
          nombre TEXT NOT NULL,
          nombre_norm TEXT NOT NULL UNIQUE
        ) STRICT;

        CREATE TABLE IF NOT EXISTS book_authors (
          book_id INTEGER NOT NULL,
          author_id INTEGER NOT NULL,
          author_order INTEGER NOT NULL DEFAULT 1,
          PRIMARY KEY (book_id, author_id),
          FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
          FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE RESTRICT
        ) STRICT;

        CREATE TABLE IF NOT EXISTS book_genres (
          book_id INTEGER NOT NULL,
          genre_id INTEGER NOT NULL,
          PRIMARY KEY (book_id, genre_id),
          FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
          FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE RESTRICT
        ) STRICT;

        CREATE UNIQUE INDEX IF NOT EXISTS ux_books_isbn13
          ON books(isbn_13)
          WHERE isbn_13 IS NOT NULL AND isbn_13 <> '';

        CREATE UNIQUE INDEX IF NOT EXISTS ux_books_isbn10
          ON books(isbn_10)
          WHERE isbn_10 IS NOT NULL AND isbn_10 <> '';

        CREATE INDEX IF NOT EXISTS idx_books_titulo ON books(titulo);
        CREATE INDEX IF NOT EXISTS idx_books_language_id ON books(language_id);
        CREATE INDEX IF NOT EXISTS idx_book_authors_author ON book_authors(author_id);
        CREATE INDEX IF NOT EXISTS idx_book_genres_genre ON book_genres(genre_id);
        """
    )


def _seed_languages(connection: sqlite3.Connection) -> None:
    for code, nombre in LANGUAGE_SEED:
        nombre_norm = matching_key(nombre)
        connection.execute(
            """
            INSERT INTO languages (code, nombre, nombre_norm)
            VALUES (?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
              nombre = excluded.nombre,
              nombre_norm = excluded.nombre_norm
            """,
            (code, nombre, nombre_norm),
        )


def _get_or_create_language_id(connection: sqlite3.Connection, language_name: str) -> int:
    clean_name = _clean_text(language_name) or "desconocido"
    normalized = matching_key(clean_name)
    row = connection.execute(
        "SELECT id FROM languages WHERE nombre_norm = ?",
        (normalized,),
    ).fetchone()
    if row:
        return int(row[0])

    code = _language_code_from_name(clean_name)
    connection.execute(
        """
        INSERT INTO languages (code, nombre, nombre_norm)
        VALUES (?, ?, ?)
        ON CONFLICT(code) DO UPDATE SET
          nombre = excluded.nombre,
          nombre_norm = excluded.nombre_norm
        """,
        (code, clean_name, normalized),
    )
    created = connection.execute("SELECT id FROM languages WHERE code = ?", (code,)).fetchone()
    if not created:
        raise RuntimeError(f"No se pudo obtener language_id para '{clean_name}'")
    return int(created[0])


def _get_or_create_author_id(connection: sqlite3.Connection, author_name: str) -> int:
    normalized = matching_key(author_name)
    row = connection.execute(
        "SELECT id FROM authors WHERE nombre_norm = ?",
        (normalized,),
    ).fetchone()
    if row:
        return int(row[0])
    connection.execute(
        "INSERT INTO authors (nombre, nombre_norm) VALUES (?, ?)",
        (author_name, normalized),
    )
    created = connection.execute(
        "SELECT id FROM authors WHERE nombre_norm = ?",
        (normalized,),
    ).fetchone()
    if not created:
        raise RuntimeError(f"No se pudo obtener author_id para '{author_name}'")
    return int(created[0])


def _get_or_create_genre_id(connection: sqlite3.Connection, genre_name: str) -> int:
    normalized = matching_key(genre_name)
    row = connection.execute(
        "SELECT id FROM genres WHERE nombre_norm = ?",
        (normalized,),
    ).fetchone()
    if row:
        return int(row[0])
    connection.execute(
        "INSERT INTO genres (nombre, nombre_norm) VALUES (?, ?)",
        (genre_name, normalized),
    )
    created = connection.execute(
        "SELECT id FROM genres WHERE nombre_norm = ?",
        (normalized,),
    ).fetchone()
    if not created:
        raise RuntimeError(f"No se pudo obtener genre_id para '{genre_name}'")
    return int(created[0])


def load_books_to_sqlite(
    input_path: Path,
    database_path: Path,
) -> tuple[int, int, int, int]:
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with input_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    connection = sqlite3.connect(database_path)
    try:
        _create_schema(connection)
        _seed_languages(connection)

        books_upserted = 0
        authors_linked = 0
        genres_linked = 0

        for row in rows:
            book_id = int(row["id"])
            language_id = _get_or_create_language_id(connection, row.get("idioma", ""))
            title = normalize_display_text(row.get("titulo", ""))
            if not title:
                title = f"Libro #{book_id}"

            connection.execute(
                """
                INSERT INTO books (
                  id, titulo, editorial, language_id, isbn_13, isbn_10, cover_url, cover_local_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  titulo = excluded.titulo,
                  editorial = excluded.editorial,
                  language_id = excluded.language_id,
                  isbn_13 = excluded.isbn_13,
                  isbn_10 = excluded.isbn_10,
                  cover_url = excluded.cover_url,
                  cover_local_path = excluded.cover_local_path
                """,
                (
                    book_id,
                    title,
                    _clean_text(row.get("editorial", "")),
                    language_id,
                    _clean_isbn13(row.get("isbn_13", "")),
                    _clean_isbn10(row.get("isbn_10", "")),
                    _clean_text(row.get("cover_url", "")),
                    _clean_text(row.get("cover_local_path", "")),
                ),
            )
            books_upserted += 1

            connection.execute("DELETE FROM book_authors WHERE book_id = ?", (book_id,))
            connection.execute("DELETE FROM book_genres WHERE book_id = ?", (book_id,))

            authors = _split_values(row.get("autor_o_autores", ""))
            for index, author_name in enumerate(authors, start=1):
                author_id = _get_or_create_author_id(connection, author_name)
                connection.execute(
                    """
                    INSERT INTO book_authors (book_id, author_id, author_order)
                    VALUES (?, ?, ?)
                    ON CONFLICT(book_id, author_id) DO UPDATE SET
                      author_order = excluded.author_order
                    """,
                    (book_id, author_id, index),
                )
                authors_linked += 1

            genres = _split_values(row.get("genero", ""))
            for genre_name in genres:
                genre_id = _get_or_create_genre_id(connection, genre_name)
                connection.execute(
                    """
                    INSERT INTO book_genres (book_id, genre_id)
                    VALUES (?, ?)
                    ON CONFLICT(book_id, genre_id) DO NOTHING
                    """,
                    (book_id, genre_id),
                )
                genres_linked += 1

        connection.commit()
        return len(rows), books_upserted, authors_linked, genres_linked
    finally:
        connection.close()
