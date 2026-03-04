from __future__ import annotations

import time
from typing import Any

import httpx

from etl.models import SourceBook
from etl.normalize import UNKNOWN_VALUE, normalize_display_text

OPENLIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"

LANGUAGE_BY_CODE = {
    "eng": "ingles",
    "en": "ingles",
    "spa": "espanol",
    "es": "espanol",
    "fre": "frances",
    "fra": "frances",
    "fr": "frances",
    "deu": "aleman",
    "ger": "aleman",
    "de": "aleman",
    "ita": "italiano",
    "it": "italiano",
    "por": "portugues",
    "pt": "portugues",
}


def _extract_isbn(values: list[str]) -> tuple[str, str]:
    isbn_13 = ""
    isbn_10 = ""
    for value in values:
        token = "".join(char for char in value if char.isdigit() or char.upper() == "X")
        if len(token) == 13 and not isbn_13:
            isbn_13 = token
        if len(token) == 10 and not isbn_10:
            isbn_10 = token
        if isbn_13 and isbn_10:
            break
    return isbn_13, isbn_10


def _language_from_openlibrary(raw_languages: list[str]) -> str:
    for entry in raw_languages:
        code = entry.rsplit("/", maxsplit=1)[-1].lower()
        if code in LANGUAGE_BY_CODE:
            return LANGUAGE_BY_CODE[code]
    return UNKNOWN_VALUE


class OpenLibrarySource:
    name = "openlibrary"

    def __init__(self, timeout_seconds: float = 12.0, retries: int = 2) -> None:
        self._client = httpx.Client(timeout=timeout_seconds, follow_redirects=True)
        self._retries = retries

    def close(self) -> None:
        self._client.close()

    def _request(self, params: dict[str, str]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                response = self._client.get(OPENLIBRARY_SEARCH_URL, params=params)
                response.raise_for_status()
                return response.json()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < self._retries:
                    time.sleep(0.5 * (2**attempt))
        return {} if last_error else {}

    def search(self, title: str, author: str, limit: int = 8) -> list[SourceBook]:
        params = {
            "title": title,
            "author": author,
            "limit": str(limit),
            "fields": "key,title,author_name,publisher,language,isbn",
        }
        payload = self._request(params)
        docs = payload.get("docs", [])

        candidates: list[SourceBook] = []
        for doc in docs:
            isbn_13, isbn_10 = _extract_isbn(doc.get("isbn", []))
            if not isbn_13 and not isbn_10:
                continue

            authors = "; ".join(normalize_display_text(name) for name in doc.get("author_name", []))
            publishers = doc.get("publisher", [])
            publisher = normalize_display_text(publishers[0]) if publishers else UNKNOWN_VALUE
            title_value = normalize_display_text(doc.get("title", ""))
            language = _language_from_openlibrary(doc.get("language", []))
            source_id = str(doc.get("key", "")).strip()

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

