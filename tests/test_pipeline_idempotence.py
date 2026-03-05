from __future__ import annotations

import csv
from pathlib import Path

from pytest import MonkeyPatch

from etl.cli import run_pipeline
from etl.models import SourceBook


class FakeResolveOpenLibrarySource:
    def search(self, title: str, author: str, limit: int = 8) -> list[SourceBook]:
        return [
            SourceBook(
                source="openlibrary",
                source_id="/works/OL1W",
                title="Deep Learning with Python",
                authors="Francois Chollet",
                publisher="Manning",
                language="ingles",
                isbn_13="9781617296864",
                isbn_10="1617296864",
            )
        ]

    def close(self) -> None:
        return None


class FakeResolveGoogleBooksSource:
    def search(self, title: str, author: str, limit: int = 8) -> list[SourceBook]:
        return []

    def close(self) -> None:
        return None


class FakeEnrichOpenLibrarySource:
    def fetch_by_isbn(self, isbn: str) -> SourceBook | None:
        return SourceBook(
            source="openlibrary",
            source_id="/books/OL1M",
            title="Deep Learning with Python",
            authors="Francois Chollet",
            publisher="Manning",
            language="ingles",
            isbn_13="9781617296864",
            isbn_10="1617296864",
        )

    def close(self) -> None:
        return None


class FakeEnrichGoogleBooksSource:
    def fetch_by_isbn(self, isbn: str) -> SourceBook | None:
        return None

    def close(self) -> None:
        return None


class FakeLibrarioSource:
    def __init__(self, token: str | None = None) -> None:
        self._token = token

    def fetch_by_isbn(self, isbn: str) -> SourceBook | None:
        return None

    def close(self) -> None:
        return None


class FakeCoverResolver:
    def __init__(self, librario_token: str | None = None) -> None:
        self._token = librario_token

    def resolve_cover_url(self, isbn: str) -> tuple[str, str]:
        return "https://example.test/cover.jpg", "google_books"

    def close(self) -> None:
        return None


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _stable_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    stable: list[dict[str, str]] = []
    for row in rows:
        item = dict(row)
        item.pop("enriched_at", None)
        stable.append(item)
    return stable


def test_pipeline_run_is_idempotent_for_business_fields(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    input_path = tmp_path / "books.csv"
    output_path = tmp_path / "books_enriched.csv"

    with input_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["autor_o_autores", "titulo", "editorial", "idioma", "genero"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "autor_o_autores": "Francois Chollet",
                "titulo": "Deep Learning with Python",
                "editorial": "Manning",
                "idioma": "ingles",
                "genero": "machine learning ai",
            }
        )

    monkeypatch.setattr("etl.resolve_isbn.OpenLibrarySource", FakeResolveOpenLibrarySource)
    monkeypatch.setattr("etl.resolve_isbn.GoogleBooksSource", FakeResolveGoogleBooksSource)
    monkeypatch.setattr("etl.enrich.OpenLibrarySource", FakeEnrichOpenLibrarySource)
    monkeypatch.setattr("etl.enrich.GoogleBooksSource", FakeEnrichGoogleBooksSource)
    monkeypatch.setattr("etl.enrich.LibrarioSource", FakeLibrarioSource)
    monkeypatch.setattr("etl.covers.MultiSourceCoverResolver", FakeCoverResolver)

    def fake_download(_url: str, destination_base: Path, timeout_seconds: float = 20.0) -> tuple[str, str]:
        destination = destination_base.with_suffix(".jpg")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"cover-image")
        return str(destination), ""

    monkeypatch.setattr("etl.covers._download_cover", fake_download)

    run_pipeline(
        input_file=str(input_path),
        output_file=str(output_path),
        min_confidence=0.75,
        limit=None,
        librario_token=None,
        min_score=0.88,
        min_title_score=0.90,
        min_authors_score=0.40,
        min_margin=0.03,
        no_online_discovery=True,
        overwrite_covers=True,
    )
    first_rows = _read_csv(output_path)

    run_pipeline(
        input_file=str(input_path),
        output_file=str(output_path),
        min_confidence=0.75,
        limit=None,
        librario_token=None,
        min_score=0.88,
        min_title_score=0.90,
        min_authors_score=0.40,
        min_margin=0.03,
        no_online_discovery=True,
        overwrite_covers=True,
    )
    second_rows = _read_csv(output_path)

    assert _stable_rows(first_rows) == _stable_rows(second_rows)
    assert second_rows[0]["cover_local_path"].endswith(".jpg")
