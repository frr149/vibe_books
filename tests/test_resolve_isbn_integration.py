from __future__ import annotations

import csv
from pathlib import Path

from pytest import MonkeyPatch

from etl.models import SourceBook
from etl.resolve_isbn import resolve_isbn


class FakeOpenLibrarySource:
    def search(self, title: str, author: str, limit: int = 8) -> list[SourceBook]:
        if title != "Deep Learning with Python":
            return []
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


class FakeGoogleBooksSource:
    def search(self, title: str, author: str, limit: int = 8) -> list[SourceBook]:
        return []

    def close(self) -> None:
        return None


def test_resolve_isbn_with_mocked_sources(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    input_path = tmp_path / "books_normalized.csv"
    candidates_path = tmp_path / "books_candidates.csv"
    resolved_path = tmp_path / "books_isbn_resolved.csv"

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
                "titulo_match",
                "autores_match",
                "editorial_match",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "id": "1",
                "titulo": "Deep Learning with Python",
                "autor_o_autores": "Francois Chollet",
                "editorial": "Manning",
                "idioma": "ingles",
                "genero": "Machine Learning / AI",
                "titulo_match": "deep learning with python",
                "autores_match": "francois chollet",
                "editorial_match": "manning",
            }
        )

    monkeypatch.setattr("etl.resolve_isbn.OpenLibrarySource", FakeOpenLibrarySource)
    monkeypatch.setattr("etl.resolve_isbn.GoogleBooksSource", FakeGoogleBooksSource)

    total_rows, resolved_count = resolve_isbn(
        input_path=input_path,
        candidates_output_path=candidates_path,
        resolved_output_path=resolved_path,
        min_confidence=0.75,
    )

    assert total_rows == 1
    assert resolved_count == 1

    with candidates_path.open(newline="", encoding="utf-8") as fh:
        candidates_rows = list(csv.DictReader(fh))
    assert len(candidates_rows) == 1
    assert candidates_rows[0]["isbn_13"] == "9781617296864"

    with resolved_path.open(newline="", encoding="utf-8") as fh:
        resolved_rows = list(csv.DictReader(fh))
    assert len(resolved_rows) == 1
    assert resolved_rows[0]["isbn_13"] == "9781617296864"
    assert resolved_rows[0]["source"] == "openlibrary"
