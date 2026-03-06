from __future__ import annotations
# ruff: noqa: E402

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.contracts import compute_pagination
from api.filters import build_book_filters
from api.repository import CatalogRepository


def _select_full_book_id(connection: sqlite3.Connection) -> int | None:
    row = connection.execute(
        """
        SELECT b.id
        FROM books b
        JOIN book_authors ba ON ba.book_id = b.id
        JOIN book_genres bg ON bg.book_id = b.id
        WHERE ((b.isbn_13 IS NOT NULL AND b.isbn_13 <> '') OR (b.isbn_10 IS NOT NULL AND b.isbn_10 <> ''))
          AND ((b.cover_url IS NOT NULL AND b.cover_url <> '') OR (b.cover_local_path IS NOT NULL AND b.cover_local_path <> ''))
        ORDER BY b.id
        LIMIT 1
        """
    ).fetchone()
    if row is not None:
        return int(row[0])
    fallback = connection.execute("SELECT id FROM books ORDER BY id LIMIT 1").fetchone()
    return int(fallback[0]) if fallback is not None else None


def _select_sparse_book_id(connection: sqlite3.Connection, full_id: int) -> int | None:
    row = connection.execute(
        """
        SELECT b.id
        FROM books b
        WHERE (b.isbn_13 IS NULL OR b.isbn_13 = '')
          AND (b.isbn_10 IS NULL OR b.isbn_10 = '')
          AND (b.cover_url IS NULL OR b.cover_url = '')
          AND (b.cover_local_path IS NULL OR b.cover_local_path = '')
          AND b.id <> ?
        ORDER BY b.id
        LIMIT 1
        """,
        (full_id,),
    ).fetchone()
    if row is not None:
        return int(row[0])

    fallback = connection.execute(
        "SELECT id FROM books WHERE id <> ? ORDER BY id LIMIT 1",
        (full_id,),
    ).fetchone()
    return int(fallback[0]) if fallback is not None else None


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def export_fixtures(db_path: Path, output_dir: Path) -> None:
    if not db_path.exists():
        raise SystemExit(f"No existe la base de datos: {db_path}")

    repository = CatalogRepository(db_path)
    connection = sqlite3.connect(db_path)
    try:
        full_id = _select_full_book_id(connection)
        if full_id is None:
            raise SystemExit("No hay libros en la base de datos para generar fixtures")
        sparse_id = _select_sparse_book_id(connection, full_id=full_id)
        if sparse_id is None:
            sparse_id = full_id
    finally:
        connection.close()

    detail_full = repository.get_book_detail(book_id=full_id)
    if detail_full is None:
        raise SystemExit(f"No se pudo obtener detalle para id={full_id}")

    detail_sparse = repository.get_book_detail(book_id=sparse_id)
    if detail_sparse is None:
        raise SystemExit(f"No se pudo obtener detalle para id={sparse_id}")

    pagination = compute_pagination(page=1, page_size=3)
    list_items, total = repository.list_books(
        filters=build_book_filters(),
        pagination=pagination,
    )
    total_pages = 0 if total == 0 else (total + pagination.page_size - 1) // pagination.page_size
    list_payload: dict[str, object] = {
        "items": [item.model_dump() for item in list_items],
        "pagination": {
            "page": pagination.page,
            "page_size": pagination.page_size,
            "total": total,
            "total_pages": total_pages,
        },
    }

    _write_json(output_dir / "book_detail_full.json", detail_full.model_dump())
    _write_json(output_dir / "book_detail_sparse.json", detail_sparse.model_dump())
    _write_json(output_dir / "books_list_page1.json", list_payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exporta fixtures reales de API desde SQLite.")
    parser.add_argument(
        "--db-path",
        default="data/books_catalog.db",
        help="Ruta a la base de datos SQLite (default: data/books_catalog.db).",
    )
    parser.add_argument(
        "--output-dir",
        default="tests/fixtures/real",
        help="Directorio de salida para fixtures JSON (default: tests/fixtures/real).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    export_fixtures(
        db_path=Path(args.db_path),
        output_dir=Path(args.output_dir),
    )


if __name__ == "__main__":
    main()
