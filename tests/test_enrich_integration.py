from __future__ import annotations

import csv
from pathlib import Path

from pytest import MonkeyPatch

from etl.enrich import enrich_from_isbn
from etl.models import SourceBook


class FakeOpenLibrarySource:
    def fetch_by_isbn(self, isbn: str) -> SourceBook | None:
        if isbn != "9781617296864":
            return None
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


class FakeGoogleBooksSource:
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


def test_enrich_from_isbn_with_mocked_sources(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    input_path = tmp_path / "books_isbn_resolved.csv"
    output_path = tmp_path / "books_enriched.csv"

    with input_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "id",
                "titulo",
                "autor_o_autores",
                "editorial",
                "idioma",
                "genero",
                "isbn_13",
                "isbn_10",
                "source",
                "source_id",
                "confidence",
                "review_status",
                "enriched_at",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "id": "1",
                "titulo": "Deep Learning with Python",
                "autor_o_autores": "desconocido",
                "editorial": "desconocido",
                "idioma": "desconocido",
                "genero": "Machine Learning / AI",
                "isbn_13": "9781617296864",
                "isbn_10": "",
                "source": "openlibrary",
                "source_id": "/works/OL1W",
                "confidence": "0.9500",
                "review_status": "auto_accepted",
                "enriched_at": "2026-01-01T00:00:00+00:00",
            }
        )

    monkeypatch.setattr("etl.enrich.OpenLibrarySource", FakeOpenLibrarySource)
    monkeypatch.setattr("etl.enrich.GoogleBooksSource", FakeGoogleBooksSource)
    monkeypatch.setattr("etl.enrich.LibrarioSource", FakeLibrarioSource)

    rows, filled_fields, conflicts = enrich_from_isbn(
        input_path=input_path,
        output_path=output_path,
        min_confidence=0.0,
    )

    assert rows == 1
    assert filled_fields == 3
    assert conflicts == 0

    with output_path.open(newline="", encoding="utf-8") as fh:
        output_rows = list(csv.DictReader(fh))
    assert len(output_rows) == 1
    assert output_rows[0]["autor_o_autores"] == "Francois Chollet"
    assert output_rows[0]["editorial"] == "Manning"
    assert output_rows[0]["idioma"] == "ingles"
    assert output_rows[0]["metadata_source"] == "openlibrary"
