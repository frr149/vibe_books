from __future__ import annotations

import csv
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, cast

import httpx


OPENLIBRARY_COVER_URL = "https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
LIBRARIO_BOOK_URL = "https://api.librario.dev/v1/book/{isbn}"


def _as_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        result: dict[str, object] = {}
        typed_value = cast(dict[object, object], value)
        for key, item in typed_value.items():
            if isinstance(key, str):
                result[key] = item
        return result
    return {}


def _as_list(value: object) -> list[object]:
    if isinstance(value, list):
        typed_value = cast(list[object], value)
        result: list[object] = []
        for item in typed_value:
            result.append(item)
        return result
    return []


def _get_str(mapping: dict[str, object], key: str) -> str:
    raw_value = mapping.get(key)
    return raw_value.strip() if isinstance(raw_value, str) else ""


class CoverResolver(Protocol):
    def resolve_cover_url(self, isbn: str) -> tuple[str, str]:
        ...

    def close(self) -> None:
        ...


class MultiSourceCoverResolver:
    def __init__(
        self,
        librario_token: str | None = None,
        timeout_seconds: float = 12.0,
        retries: int = 2,
    ) -> None:
        self._token = librario_token or os.getenv("LIBRARIO_API_TOKEN", "")
        self._retries = retries
        self._client = httpx.Client(timeout=timeout_seconds, follow_redirects=True)

    def close(self) -> None:
        self._client.close()

    def _request_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, object]:
        for attempt in range(self._retries + 1):
            try:
                response = self._client.get(url, headers=headers, params=params)
                if response.status_code == 404:
                    return {}
                response.raise_for_status()
                return _as_dict(response.json())
            except Exception:  # noqa: BLE001
                if attempt < self._retries:
                    time.sleep(0.4 * (2**attempt))
        return {}

    def _resolve_from_librario(self, isbn: str) -> str:
        if not self._token:
            return ""
        payload = self._request_json(
            LIBRARIO_BOOK_URL.format(isbn=isbn),
            headers={"Authorization": f"Bearer {self._token}"},
        )
        publication = _as_dict(payload.get("publication"))
        return _get_str(publication, "cover")

    def _resolve_from_google_books(self, isbn: str) -> str:
        payload = self._request_json(
            GOOGLE_BOOKS_URL,
            params={
                "q": f"isbn:{isbn}",
                "printType": "books",
                "maxResults": "1",
            },
        )
        items = _as_list(payload.get("items"))
        if not items:
            return ""
        first_item = _as_dict(items[0])
        volume_info = _as_dict(first_item.get("volumeInfo"))
        image_links = _as_dict(volume_info.get("imageLinks"))
        for key in ("extraLarge", "large", "medium", "small", "thumbnail", "smallThumbnail"):
            url = _get_str(image_links, key)
            if url:
                return url.replace("http://", "https://")
        return ""

    def resolve_cover_url(self, isbn: str) -> tuple[str, str]:
        librario_cover = self._resolve_from_librario(isbn)
        if librario_cover:
            return librario_cover, "librario"

        google_cover = self._resolve_from_google_books(isbn)
        if google_cover:
            return google_cover, "google_books"

        return OPENLIBRARY_COVER_URL.format(isbn=isbn), "openlibrary"


def _clean_isbn(row: dict[str, str]) -> str:
    isbn13 = "".join(char for char in row.get("isbn_13", "") if char.isdigit())
    isbn10 = "".join(char for char in row.get("isbn_10", "") if char.isdigit() or char.upper() == "X")
    return isbn13 or isbn10


def _detect_extension(content_type: str) -> str:
    lowered = content_type.lower()
    if "png" in lowered:
        return ".png"
    if "webp" in lowered:
        return ".webp"
    return ".jpg"


def _download_cover(url: str, destination_base: Path, timeout_seconds: float = 20.0) -> tuple[str, str]:
    try:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
            response = client.get(url)
            if response.status_code != 200:
                return "", f"http_{response.status_code}"
            content_type = response.headers.get("content-type", "")
            if "image" not in content_type.lower():
                return "", "invalid_content_type"
            extension = _detect_extension(content_type)
            destination = destination_base.with_suffix(extension)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(response.content)
            return str(destination), ""
    except Exception as exc:  # noqa: BLE001
        return "", f"error:{exc.__class__.__name__}"


def fetch_covers(
    input_path: Path,
    output_enriched_path: Path,
    covers_dir: Path,
    manifest_output_path: Path,
    *,
    overwrite: bool = False,
    limit: int | None = None,
    resolver: CoverResolver | None = None,
) -> tuple[int, int, int, int]:
    with input_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    rows_to_process = rows if limit is None else rows[:limit]

    own_resolver = False
    if resolver is None:
        resolver = MultiSourceCoverResolver()
        own_resolver = True

    downloaded = 0
    skipped = 0
    errors = 0
    manifest_rows: list[dict[str, str]] = []

    try:
        for row in rows_to_process:
            row.setdefault("cover_url", "")
            row.setdefault("cover_source", "")
            row.setdefault("cover_local_path", "")

            book_id = str(row.get("id", "")).strip()
            isbn = _clean_isbn(row)
            if not isbn:
                skipped += 1
                manifest_rows.append(
                    {
                        "id": book_id,
                        "isbn": "",
                        "cover_url": "",
                        "cover_source": "",
                        "local_path": "",
                        "status": "no_isbn",
                        "error": "",
                        "downloaded_at": "",
                    }
                )
                continue

            file_base = covers_dir / f"{book_id}_{isbn}"
            existing = [path for path in file_base.parent.glob(f"{file_base.name}.*") if path.is_file()]
            if existing and not overwrite:
                skipped += 1
                chosen = str(existing[0])
                row["cover_local_path"] = chosen
                status = "already_exists"
                manifest_rows.append(
                    {
                        "id": book_id,
                        "isbn": isbn,
                        "cover_url": row.get("cover_url", ""),
                        "cover_source": row.get("cover_source", ""),
                        "local_path": chosen,
                        "status": status,
                        "error": "",
                        "downloaded_at": "",
                    }
                )
                continue

            cover_url, cover_source = resolver.resolve_cover_url(isbn)
            if not cover_url:
                errors += 1
                manifest_rows.append(
                    {
                        "id": book_id,
                        "isbn": isbn,
                        "cover_url": "",
                        "cover_source": "",
                        "local_path": "",
                        "status": "no_cover_url",
                        "error": "",
                        "downloaded_at": "",
                    }
                )
                continue

            local_path, error = _download_cover(cover_url, file_base)
            if not local_path:
                errors += 1
                manifest_rows.append(
                    {
                        "id": book_id,
                        "isbn": isbn,
                        "cover_url": cover_url,
                        "cover_source": cover_source,
                        "local_path": "",
                        "status": "download_error",
                        "error": error,
                        "downloaded_at": "",
                    }
                )
                continue

            downloaded += 1
            row["cover_url"] = cover_url
            row["cover_source"] = cover_source
            row["cover_local_path"] = local_path
            manifest_rows.append(
                {
                    "id": book_id,
                    "isbn": isbn,
                    "cover_url": cover_url,
                    "cover_source": cover_source,
                    "local_path": local_path,
                    "status": "downloaded",
                    "error": "",
                    "downloaded_at": datetime.now(timezone.utc).isoformat(),
                }
            )
    finally:
        if own_resolver:
            resolver.close()

    output_enriched_path.parent.mkdir(parents=True, exist_ok=True)
    with output_enriched_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)

    manifest_output_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "id",
                "isbn",
                "cover_url",
                "cover_source",
                "local_path",
                "status",
                "error",
                "downloaded_at",
            ],
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    return len(rows_to_process), downloaded, skipped, errors
