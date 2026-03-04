from __future__ import annotations

import os
import time
from typing import Any

import httpx

from etl.models import SourceBook
from etl.normalize import UNKNOWN_VALUE, normalize_display_text

LIBRARIO_URL_TEMPLATE = "https://api.librario.dev/v1/book/{isbn}"

LANGUAGE_BY_CODE = {
    "en": "ingles",
    "es": "espanol",
    "fr": "frances",
    "de": "aleman",
    "it": "italiano",
    "pt": "portugues",
}


class LibrarioSource:
    name = "librario"

    def __init__(
        self,
        token: str | None = None,
        timeout_seconds: float = 12.0,
        retries: int = 2,
    ) -> None:
        self._token = token or os.getenv("LIBRARIO_API_TOKEN", "")
        self._retries = retries
        self._client = httpx.Client(timeout=timeout_seconds, follow_redirects=True)

    @property
    def enabled(self) -> bool:
        return bool(self._token)

    def close(self) -> None:
        self._client.close()

    def _request(self, isbn: str) -> dict[str, Any]:
        if not self.enabled:
            return {}
        last_error: Exception | None = None
        headers = {"Authorization": f"Bearer {self._token}"}
        for attempt in range(self._retries + 1):
            try:
                response = self._client.get(
                    LIBRARIO_URL_TEMPLATE.format(isbn=isbn),
                    headers=headers,
                )
                if response.status_code == 404:
                    return {}
                response.raise_for_status()
                return response.json()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < self._retries:
                    time.sleep(0.5 * (2**attempt))
        return {} if last_error else {}

    def fetch_by_isbn(self, isbn: str) -> SourceBook | None:
        payload = self._request(isbn)
        if not payload:
            return None

        title_data = payload.get("title", {})
        title_value = normalize_display_text(title_data.get("main", ""))

        contributors = payload.get("contributors", [])
        authors = "; ".join(
            normalize_display_text(item.get("name", ""))
            for item in contributors
            if str(item.get("role", "")).lower() == "author"
        )

        publication = payload.get("publication", {})
        publisher_info = publication.get("publisher", {})
        publisher = normalize_display_text(publisher_info.get("name", UNKNOWN_VALUE))
        language_code = str(publication.get("language", "")).lower()
        language = LANGUAGE_BY_CODE.get(language_code, UNKNOWN_VALUE)

        identifiers = payload.get("identifiers", {})
        isbn_13 = normalize_display_text(identifiers.get("isbn13", ""))
        isbn_10 = normalize_display_text(identifiers.get("isbn10", ""))

        return SourceBook(
            source=self.name,
            source_id=isbn_13 or isbn_10 or isbn,
            title=title_value or UNKNOWN_VALUE,
            authors=authors or UNKNOWN_VALUE,
            publisher=publisher or UNKNOWN_VALUE,
            language=language,
            isbn_13=isbn_13,
            isbn_10=isbn_10,
        )

