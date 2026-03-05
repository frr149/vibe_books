from __future__ import annotations

import csv
from pathlib import Path

from pytest import MonkeyPatch

from etl.covers import fetch_covers


class DummyResolver:
    def resolve_cover_url(self, isbn: str) -> tuple[str, str]:
        if isbn == "9781111111111":
            return "https://example.test/cover.jpg", "google_books"
        return "", ""

    def close(self) -> None:
        return None


def test_fetch_covers_writes_manifest_and_updates_csv(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    input_path = tmp_path / "books_enriched.csv"
    output_path = tmp_path / "books_enriched_out.csv"
    covers_dir = tmp_path / "covers"
    manifest_path = tmp_path / "covers_manifest.csv"

    rows: list[dict[str, str]] = [
        {
            "id": "1",
            "titulo": "Libro 1",
            "autor_o_autores": "Autor 1",
            "editorial": "Editorial 1",
            "idioma": "ingles",
            "genero": "Programacion",
            "isbn_13": "9781111111111",
            "isbn_10": "",
            "source": "",
            "source_id": "",
            "confidence": "0.90",
            "review_status": "auto_accepted",
            "metadata_source": "",
            "metadata_confidence": "0.00",
            "conflict_notes": "",
            "enriched_at": "2026-03-04T00:00:00+00:00",
        },
        {
            "id": "2",
            "titulo": "Libro 2",
            "autor_o_autores": "Autor 2",
            "editorial": "Editorial 2",
            "idioma": "ingles",
            "genero": "Programacion",
            "isbn_13": "",
            "isbn_10": "",
            "source": "",
            "source_id": "",
            "confidence": "0.50",
            "review_status": "unresolved",
            "metadata_source": "",
            "metadata_confidence": "0.00",
            "conflict_notes": "",
            "enriched_at": "2026-03-04T00:00:00+00:00",
        },
    ]
    with input_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    def fake_download(_url: str, destination_base: Path, timeout_seconds: float = 20.0) -> tuple[str, str]:
        path = destination_base.with_suffix(".jpg")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake-image")
        return str(path), ""

    monkeypatch.setattr("etl.covers._download_cover", fake_download)

    total, downloaded, skipped, errors = fetch_covers(
        input_path=input_path,
        output_enriched_path=output_path,
        covers_dir=covers_dir,
        manifest_output_path=manifest_path,
        resolver=DummyResolver(),
    )

    assert total == 2
    assert downloaded == 1
    assert skipped == 1
    assert errors == 0

    with output_path.open(newline="", encoding="utf-8") as fh:
        output_rows = list(csv.DictReader(fh))
    assert output_rows[0]["cover_source"] == "google_books"
    assert output_rows[0]["cover_url"] == "https://example.test/cover.jpg"
    assert output_rows[0]["cover_local_path"].endswith(".jpg")
    assert output_rows[1]["cover_local_path"] == ""

    with manifest_path.open(newline="", encoding="utf-8") as fh:
        manifest_rows = list(csv.DictReader(fh))
    assert len(manifest_rows) == 2
    assert manifest_rows[0]["status"] == "downloaded"
    assert manifest_rows[1]["status"] == "no_isbn"
