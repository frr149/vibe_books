from __future__ import annotations

import sqlite3
from pathlib import Path

from etl.normalize import matching_key

from api.contracts import Pagination
from api.filters import BookFilters
from api.schemas import Author, BookDetail, BookListItem, Genre, Language


def _slug_from_norm(value: str) -> str:
    return "-".join(part for part in value.strip().split(" ") if part)


class CatalogRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _build_books_conditions(self, filters: BookFilters) -> tuple[list[str], list[str], list[object]]:
        joins: list[str] = []
        conditions: list[str] = []
        params: list[object] = []

        if filters.author is not None or filters.author_id is not None:
            joins.extend(
                [
                    "JOIN book_authors ba ON ba.book_id = b.id",
                    "JOIN authors a ON a.id = ba.author_id",
                ]
            )
        if filters.genre is not None or filters.genre_id is not None:
            joins.extend(
                [
                    "JOIN book_genres bg ON bg.book_id = b.id",
                    "JOIN genres g ON g.id = bg.genre_id",
                ]
            )

        if filters.q is not None:
            conditions.append("b.titulo LIKE ?")
            params.append(f"%{filters.q}%")

        if filters.language is not None:
            normalized_language = matching_key(filters.language)
            conditions.append("(l.nombre_norm = ? OR lower(l.code) = ?)")
            params.append(normalized_language)
            params.append(normalized_language[:2])

        if filters.has_isbn is True:
            conditions.append("((b.isbn_13 IS NOT NULL AND b.isbn_13 <> '') OR (b.isbn_10 IS NOT NULL AND b.isbn_10 <> ''))")
        if filters.has_isbn is False:
            conditions.append("((b.isbn_13 IS NULL OR b.isbn_13 = '') AND (b.isbn_10 IS NULL OR b.isbn_10 = ''))")

        if filters.author is not None:
            conditions.append("a.nombre_norm = ?")
            params.append(matching_key(filters.author))
        if filters.author_id is not None:
            conditions.append("ba.author_id = ?")
            params.append(filters.author_id)

        if filters.genre is not None:
            conditions.append("g.nombre_norm = ?")
            params.append(matching_key(filters.genre))
        if filters.genre_id is not None:
            conditions.append("bg.genre_id = ?")
            params.append(filters.genre_id)

        return joins, conditions, params

    def list_books(self, *, filters: BookFilters, pagination: Pagination) -> tuple[list[BookListItem], int]:
        joins, conditions, params = self._build_books_conditions(filters)
        joins_sql = " ".join(joins)
        where_sql = ""
        if conditions:
            where_sql = "WHERE " + " AND ".join(conditions)

        count_sql = (
            "SELECT COUNT(DISTINCT b.id) AS total "
            "FROM books b "
            "JOIN languages l ON l.id = b.language_id "
            f"{joins_sql} "
            f"{where_sql}"
        )
        data_sql = (
            "SELECT DISTINCT "
            "b.id, b.titulo, b.editorial, l.nombre AS idioma, b.isbn_13, b.isbn_10, b.cover_url "
            "FROM books b "
            "JOIN languages l ON l.id = b.language_id "
            f"{joins_sql} "
            f"{where_sql} "
            "ORDER BY b.id "
            "LIMIT ? OFFSET ?"
        )

        with self._connect() as connection:
            count_row = connection.execute(count_sql, tuple(params)).fetchone()
            total = int(count_row["total"]) if count_row is not None else 0

            data_params = [*params, pagination.limit, pagination.offset]
            rows = connection.execute(data_sql, tuple(data_params)).fetchall()

        items: list[BookListItem] = []
        for row in rows:
            items.append(
                BookListItem(
                    id=int(row["id"]),
                    titulo=str(row["titulo"]),
                    editorial=str(row["editorial"]) if row["editorial"] is not None else None,
                    idioma=str(row["idioma"]),
                    isbn_13=str(row["isbn_13"]) if row["isbn_13"] is not None else None,
                    isbn_10=str(row["isbn_10"]) if row["isbn_10"] is not None else None,
                    cover_url=str(row["cover_url"]) if row["cover_url"] is not None else None,
                )
            )
        return items, total

    def get_book_detail(self, *, book_id: int) -> BookDetail | None:
        with self._connect() as connection:
            book_row = connection.execute(
                """
                SELECT b.id, b.titulo, b.editorial, b.isbn_13, b.isbn_10, b.cover_url, b.cover_local_path,
                       l.id AS language_id, l.code AS language_code, l.nombre AS language_nombre
                FROM books b
                JOIN languages l ON l.id = b.language_id
                WHERE b.id = ?
                """,
                (book_id,),
            ).fetchone()
            if book_row is None:
                return None

            author_rows = connection.execute(
                """
                SELECT a.id, a.nombre, a.nombre_norm,
                       (SELECT COUNT(*) FROM book_authors ba2 WHERE ba2.author_id = a.id) AS book_count
                FROM book_authors ba
                JOIN authors a ON a.id = ba.author_id
                WHERE ba.book_id = ?
                ORDER BY ba.author_order, a.id
                """,
                (book_id,),
            ).fetchall()
            genre_rows = connection.execute(
                """
                SELECT g.id, g.nombre, g.nombre_norm,
                       (SELECT COUNT(*) FROM book_genres bg2 WHERE bg2.genre_id = g.id) AS book_count
                FROM book_genres bg
                JOIN genres g ON g.id = bg.genre_id
                WHERE bg.book_id = ?
                ORDER BY g.nombre
                """,
                (book_id,),
            ).fetchall()

        language = Language(
            id=int(book_row["language_id"]),
            code=str(book_row["language_code"]),
            nombre=str(book_row["language_nombre"]),
        )

        authors: list[Author] = []
        for row in author_rows:
            name_norm = str(row["nombre_norm"])
            authors.append(
                Author(
                    id=int(row["id"]),
                    nombre=str(row["nombre"]),
                    slug=_slug_from_norm(name_norm),
                    book_count=int(row["book_count"]),
                )
            )

        genres: list[Genre] = []
        for row in genre_rows:
            name_norm = str(row["nombre_norm"])
            genres.append(
                Genre(
                    id=int(row["id"]),
                    nombre=str(row["nombre"]),
                    slug=_slug_from_norm(name_norm),
                    book_count=int(row["book_count"]),
                )
            )

        return BookDetail(
            id=int(book_row["id"]),
            titulo=str(book_row["titulo"]),
            editorial=str(book_row["editorial"]) if book_row["editorial"] is not None else None,
            idioma=str(book_row["language_nombre"]),
            isbn_13=str(book_row["isbn_13"]) if book_row["isbn_13"] is not None else None,
            isbn_10=str(book_row["isbn_10"]) if book_row["isbn_10"] is not None else None,
            cover_url=str(book_row["cover_url"]) if book_row["cover_url"] is not None else None,
            cover_local_path=str(book_row["cover_local_path"]) if book_row["cover_local_path"] is not None else None,
            authors=authors,
            genres=genres,
            language=language,
        )

    def list_authors(self) -> list[Author]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT a.id, a.nombre, a.nombre_norm, COUNT(DISTINCT ba.book_id) AS book_count
                FROM authors a
                JOIN book_authors ba ON ba.author_id = a.id
                GROUP BY a.id, a.nombre, a.nombre_norm
                ORDER BY a.nombre
                """
            ).fetchall()

        items: list[Author] = []
        for row in rows:
            name_norm = str(row["nombre_norm"])
            items.append(
                Author(
                    id=int(row["id"]),
                    nombre=str(row["nombre"]),
                    slug=_slug_from_norm(name_norm),
                    book_count=int(row["book_count"]),
                )
            )
        return items

    def list_genres(self) -> list[Genre]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT g.id, g.nombre, g.nombre_norm, COUNT(DISTINCT bg.book_id) AS book_count
                FROM genres g
                JOIN book_genres bg ON bg.genre_id = g.id
                GROUP BY g.id, g.nombre, g.nombre_norm
                ORDER BY g.nombre
                """
            ).fetchall()

        items: list[Genre] = []
        for row in rows:
            name_norm = str(row["nombre_norm"])
            items.append(
                Genre(
                    id=int(row["id"]),
                    nombre=str(row["nombre"]),
                    slug=_slug_from_norm(name_norm),
                    book_count=int(row["book_count"]),
                )
            )
        return items

    def list_languages(self) -> list[Language]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT l.id, l.code, l.nombre
                FROM languages l
                JOIN books b ON b.language_id = l.id
                GROUP BY l.id, l.code, l.nombre
                ORDER BY l.nombre
                """
            ).fetchall()

        items: list[Language] = []
        for row in rows:
            items.append(
                Language(
                    id=int(row["id"]),
                    code=str(row["code"]),
                    nombre=str(row["nombre"]),
                )
            )
        return items
