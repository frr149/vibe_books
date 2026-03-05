from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from etl.load_sqlite import load_books_to_sqlite


CSV_FIELDS = [
    "id",
    "titulo",
    "autor_o_autores",
    "editorial",
    "idioma",
    "genero",
    "isbn_13",
    "isbn_10",
    "source",
    "source_id",
    "confidence",
    "review_status",
    "metadata_source",
    "metadata_confidence",
    "conflict_notes",
    "enriched_at",
    "cover_url",
    "cover_source",
    "cover_local_path",
]


def _write_enriched_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def test_load_sqlite_creates_schema_and_relations(tmp_path: Path) -> None:
    input_path = tmp_path / "books_enriched.csv"
    db_path = tmp_path / "books_catalog.db"
    rows = [
        {
            "id": "1",
            "titulo": "Libro Uno",
            "autor_o_autores": "Autor Uno; Autor Dos",
            "editorial": "Manning",
            "idioma": "ingles",
            "genero": "Programacion; Data Science",
            "isbn_13": "9781617296864",
            "isbn_10": "1617296864",
            "source": "",
            "source_id": "",
            "confidence": "1.0000",
            "review_status": "auto_accepted",
            "metadata_source": "",
            "metadata_confidence": "0.0000",
            "conflict_notes": "",
            "enriched_at": "2026-03-05T00:00:00+00:00",
            "cover_url": "https://example.test/book1.jpg",
            "cover_source": "google_books",
            "cover_local_path": "data/covers/1_9781617296864.jpg",
        },
        {
            "id": "2",
            "titulo": "Libro Dos",
            "autor_o_autores": "Autor Uno",
            "editorial": "desconocido",
            "idioma": "frances",
            "genero": "Programacion",
            "isbn_13": "",
            "isbn_10": "",
            "source": "",
            "source_id": "",
            "confidence": "0.5000",
            "review_status": "needs_review",
            "metadata_source": "",
            "metadata_confidence": "0.0000",
            "conflict_notes": "",
            "enriched_at": "2026-03-05T00:00:00+00:00",
            "cover_url": "",
            "cover_source": "",
            "cover_local_path": "",
        },
    ]
    _write_enriched_csv(input_path, rows)

    rows_read, books_upserted, authors_linked, genres_linked = load_books_to_sqlite(
        input_path=input_path,
        database_path=db_path,
    )

    assert rows_read == 2
    assert books_upserted == 2
    assert authors_linked == 3
    assert genres_linked == 3

    connection = sqlite3.connect(db_path)
    try:
        books_count = connection.execute("SELECT COUNT(*) FROM books").fetchone()
        assert books_count is not None
        assert int(books_count[0]) == 2

        authors_count = connection.execute("SELECT COUNT(*) FROM authors").fetchone()
        assert authors_count is not None
        assert int(authors_count[0]) == 2

        genres_count = connection.execute("SELECT COUNT(*) FROM genres").fetchone()
        assert genres_count is not None
        assert int(genres_count[0]) == 2

        book_authors_count = connection.execute("SELECT COUNT(*) FROM book_authors").fetchone()
        assert book_authors_count is not None
        assert int(book_authors_count[0]) == 3

        book_genres_count = connection.execute("SELECT COUNT(*) FROM book_genres").fetchone()
        assert book_genres_count is not None
        assert int(book_genres_count[0]) == 3

        languages_count = connection.execute("SELECT COUNT(*) FROM languages").fetchone()
        assert languages_count is not None
        assert int(languages_count[0]) >= 4

        language_row = connection.execute(
            """
            SELECT l.code
            FROM books b
            JOIN languages l ON l.id = b.language_id
            WHERE b.id = 1
            """
        ).fetchone()
        assert language_row == ("en",)

        editorial_row = connection.execute("SELECT editorial FROM books WHERE id = 2").fetchone()
        assert editorial_row == (None,)
    finally:
        connection.close()


def test_load_sqlite_is_idempotent_for_relations(tmp_path: Path) -> None:
    input_path = tmp_path / "books_enriched.csv"
    db_path = tmp_path / "books_catalog.db"

    first_rows = [
        {
            "id": "10",
            "titulo": "Libro Cambiante",
            "autor_o_autores": "Autor A",
            "editorial": "Manning",
            "idioma": "ingles",
            "genero": "Programacion",
            "isbn_13": "9781617296864",
            "isbn_10": "1617296864",
            "source": "",
            "source_id": "",
            "confidence": "1.0000",
            "review_status": "auto_accepted",
            "metadata_source": "",
            "metadata_confidence": "0.0000",
            "conflict_notes": "",
            "enriched_at": "2026-03-05T00:00:00+00:00",
            "cover_url": "",
            "cover_source": "",
            "cover_local_path": "",
        }
    ]
    _write_enriched_csv(input_path, first_rows)
    load_books_to_sqlite(input_path=input_path, database_path=db_path)

    second_rows = [
        {
            "id": "10",
            "titulo": "Libro Cambiante",
            "autor_o_autores": "Autor A; Autor B",
            "editorial": "Manning",
            "idioma": "ingles",
            "genero": "Programacion; Data Science",
            "isbn_13": "9781617296864",
            "isbn_10": "1617296864",
            "source": "",
            "source_id": "",
            "confidence": "1.0000",
            "review_status": "auto_accepted",
            "metadata_source": "",
            "metadata_confidence": "0.0000",
            "conflict_notes": "",
            "enriched_at": "2026-03-05T00:00:00+00:00",
            "cover_url": "",
            "cover_source": "",
            "cover_local_path": "",
        }
    ]
    _write_enriched_csv(input_path, second_rows)
    load_books_to_sqlite(input_path=input_path, database_path=db_path)

    connection = sqlite3.connect(db_path)
    try:
        book_authors_count = connection.execute(
            "SELECT COUNT(*) FROM book_authors WHERE book_id = 10"
        ).fetchone()
        assert book_authors_count is not None
        assert int(book_authors_count[0]) == 2

        book_genres_count = connection.execute(
            "SELECT COUNT(*) FROM book_genres WHERE book_id = 10"
        ).fetchone()
        assert book_genres_count is not None
        assert int(book_genres_count[0]) == 2
    finally:
        connection.close()
