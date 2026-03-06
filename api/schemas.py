from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Author(StrictSchema):
    id: int
    nombre: str
    slug: str
    book_count: int


class Genre(StrictSchema):
    id: int
    nombre: str
    slug: str
    book_count: int


class Language(StrictSchema):
    id: int
    code: str
    nombre: str


class BookListItem(StrictSchema):
    id: int
    titulo: str
    editorial: str | None
    idioma: str
    isbn_13: str | None
    isbn_10: str | None
    cover_url: str | None


class BookDetail(StrictSchema):
    id: int
    titulo: str
    editorial: str | None
    idioma: str
    isbn_13: str | None
    isbn_10: str | None
    cover_url: str | None
    cover_local_path: str | None
    authors: list[Author]
    genres: list[Genre]
    language: Language
