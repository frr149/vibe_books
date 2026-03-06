from __future__ import annotations

import math
import sqlite3
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from api.contracts import build_error_payload, compute_pagination
from api.filters import build_book_filters
from api.repository import CatalogRepository

DB_PATH = Path("data/books_catalog.db")
api_router = APIRouter(prefix="/api/v1")


@api_router.get("/health")
def health() -> dict[str, str]:
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="database_not_found")
    try:
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute("SELECT 1")
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="database_unavailable") from exc
    return {"status": "ok"}


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=build_error_payload(
            code=code,
            message=message,
            details=details,
        ),
    )


@api_router.get("/books")
def list_books(
    page: int = 1,
    page_size: int = 20,
    q: str | None = None,
    language: str | None = None,
    author: str | None = None,
    author_id: int | None = None,
    genre: str | None = None,
    genre_id: int | None = None,
    has_isbn: bool | None = None,
) -> JSONResponse:
    try:
        pagination = compute_pagination(page=page, page_size=page_size)
        filters = build_book_filters(
            q=q,
            language=language,
            author=author,
            author_id=author_id,
            genre=genre,
            genre_id=genre_id,
            has_isbn=has_isbn,
        )
    except ValueError as exc:
        return _error_response(
            status_code=422,
            code="invalid_query",
            message=str(exc),
        )

    try:
        repository = CatalogRepository(DB_PATH)
        items, total = repository.list_books(filters=filters, pagination=pagination)
    except sqlite3.Error:
        return _error_response(
            status_code=503,
            code="database_unavailable",
            message="No se pudo consultar la base de datos",
        )

    total_pages = 0 if total == 0 else int(math.ceil(total / pagination.page_size))
    return JSONResponse(
        status_code=200,
        content={
            "items": [item.model_dump() for item in items],
            "pagination": {
                "page": pagination.page,
                "page_size": pagination.page_size,
                "total": total,
                "total_pages": total_pages,
            },
        },
    )


@api_router.get("/books/{book_id}")
def get_book_detail(book_id: int) -> JSONResponse:
    try:
        repository = CatalogRepository(DB_PATH)
        detail = repository.get_book_detail(book_id=book_id)
    except sqlite3.Error:
        return _error_response(
            status_code=503,
            code="database_unavailable",
            message="No se pudo consultar la base de datos",
        )

    if detail is None:
        return _error_response(
            status_code=404,
            code="book_not_found",
            message=f"No existe un libro con id={book_id}",
        )
    return JSONResponse(
        status_code=200,
        content=detail.model_dump(),
    )


@api_router.get("/authors")
def list_authors() -> JSONResponse:
    try:
        repository = CatalogRepository(DB_PATH)
        items = repository.list_authors()
    except sqlite3.Error:
        return _error_response(
            status_code=503,
            code="database_unavailable",
            message="No se pudo consultar la base de datos",
        )
    return JSONResponse(
        status_code=200,
        content={"items": [item.model_dump() for item in items]},
    )


@api_router.get("/genres")
def list_genres() -> JSONResponse:
    try:
        repository = CatalogRepository(DB_PATH)
        items = repository.list_genres()
    except sqlite3.Error:
        return _error_response(
            status_code=503,
            code="database_unavailable",
            message="No se pudo consultar la base de datos",
        )
    return JSONResponse(
        status_code=200,
        content={"items": [item.model_dump() for item in items]},
    )


@api_router.get("/languages")
def list_languages() -> JSONResponse:
    try:
        repository = CatalogRepository(DB_PATH)
        items = repository.list_languages()
    except sqlite3.Error:
        return _error_response(
            status_code=503,
            code="database_unavailable",
            message="No se pudo consultar la base de datos",
        )
    return JSONResponse(
        status_code=200,
        content={"items": [item.model_dump() for item in items]},
    )


def create_app() -> FastAPI:
    app = FastAPI(title="Vibe Books API", version="0.1.0")
    app.include_router(api_router)
    return app


app = create_app()
