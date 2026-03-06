from __future__ import annotations

from pydantic import BaseModel


class Author(BaseModel):
    id: int
    nombre: str
    slug: str
    book_count: int


class Genre(BaseModel):
    id: int
    nombre: str
    slug: str
    book_count: int


class Language(BaseModel):
    id: int
    code: str
    nombre: str


class BookListItem(BaseModel):
    id: int
    titulo: str
    editorial: str | None
    idioma: str
    isbn_13: str | None
    isbn_10: str | None
    cover_url: str | None


class BookDetail(BaseModel):
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
