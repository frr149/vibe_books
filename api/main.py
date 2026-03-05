from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException

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


def create_app() -> FastAPI:
    app = FastAPI(title="Vibe Books API", version="0.1.0")
    app.include_router(api_router)
    return app


app = create_app()
