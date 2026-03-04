from __future__ import annotations

import time
from typing import Any

import httpx

from etl.models import SourceBook
from etl.normalize import UNKNOWN_VALUE, normalize_display_text

GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"

LANGUAGE_BY_CODE = {
    "en": "ingles",
    "es": "espanol",
    "fr": "frances",
    "de": "aleman",
    "it": "italiano",
    "pt": "portugues",
}


def _extract_isbn(identifiers: list[dict[str, Any]]) -> tuple[str, str]:
    isbn_13 = ""
    isbn_10 = ""
    for item in identifiers:
        id_type = str(item.get("type", "")).upper()
        identifier = "".join(
            char for char in str(item.get("identifier", "")) if char.isdigit() or char.upper() == "X"
        )
        if id_type == "ISBN_13" and len(identifier) == 13 and not isbn_13:
            isbn_13 = identifier
        if id_type == "ISBN_10" and len(identifier) == 10 and not isbn_10:
            isbn_10 = identifier
    return isbn_13, isbn_10


def _language_from_google(raw_code: str) -> str:
    code = raw_code.lower()
    return LANGUAGE_BY_CODE.get(code, UNKNOWN_VALUE)


class GoogleBooksSource:
    name = "google_books"

    def __init__(self, timeout_seconds: float = 12.0, retries: int = 2) -> None:
        self._client = httpx.Client(timeout=timeout_seconds, follow_redirects=True)
        self._retries = retries

    def close(self) -> None:
        self._client.close()

    def _request(self, params: dict[str, str]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                response = self._client.get(GOOGLE_BOOKS_URL, params=params)
                response.raise_for_status()
                return response.json()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < self._retries:
                    time.sleep(0.5 * (2**attempt))
        return {} if last_error else {}

    def search(self, title: str, author: str, limit: int = 8) -> list[SourceBook]:
        if author:
            query = f'intitle:"{title}" inauthor:"{author}"'
        else:
            query = f'intitle:"{title}"'
        params = {
            "q": query,
            "printType": "books",
            "maxResults": str(max(1, min(limit, 40))),
        }

        payload = self._request(params)
        items = payload.get("items", [])

        candidates: list[SourceBook] = []
        for item in items:
            volume_info = item.get("volumeInfo", {})
            isbn_13, isbn_10 = _extract_isbn(volume_info.get("industryIdentifiers", []))
            if not isbn_13 and not isbn_10:
                continue

            title_value = normalize_display_text(volume_info.get("title", ""))
            authors = "; ".join(
                normalize_display_text(name) for name in volume_info.get("authors", [])
            )
            publisher = normalize_display_text(volume_info.get("publisher", UNKNOWN_VALUE))
            language = _language_from_google(str(volume_info.get("language", "")))
            source_id = str(item.get("id", "")).strip()

            candidates.append(
                SourceBook(
                    source=self.name,
                    source_id=source_id,
                    title=title_value or UNKNOWN_VALUE,
                    authors=authors or UNKNOWN_VALUE,
                    publisher=publisher or UNKNOWN_VALUE,
                    language=language,
                    isbn_13=isbn_13,
                    isbn_10=isbn_10,
                )
            )
        return candidates

    def fetch_by_isbn(self, isbn: str) -> SourceBook | None:
        params = {
            "q": f"isbn:{isbn}",
            "printType": "books",
            "maxResults": "1",
        }
        payload = self._request(params)
        items = payload.get("items", [])
        if not items:
            return None

        item = items[0]
        volume_info = item.get("volumeInfo", {})
        isbn_13, isbn_10 = _extract_isbn(volume_info.get("industryIdentifiers", []))
        if not isbn_13 and not isbn_10:
            isbn_13, isbn_10 = _extract_isbn(
                [{"type": "ISBN_13", "identifier": isbn}],
            )

        title_value = normalize_display_text(volume_info.get("title", ""))
        authors = "; ".join(
            normalize_display_text(name) for name in volume_info.get("authors", [])
        )
        publisher = normalize_display_text(volume_info.get("publisher", UNKNOWN_VALUE))
        language = _language_from_google(str(volume_info.get("language", "")))
        source_id = str(item.get("id", "")).strip()
        return SourceBook(
            source=self.name,
            source_id=source_id or isbn,
            title=title_value or UNKNOWN_VALUE,
            authors=authors or UNKNOWN_VALUE,
            publisher=publisher or UNKNOWN_VALUE,
            language=language,
            isbn_13=isbn_13,
            isbn_10=isbn_10,
        )
