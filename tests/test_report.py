from __future__ import annotations

import csv
import json
from pathlib import Path

from etl.report import run_phase4


def test_run_phase4_generates_review_and_report(tmp_path: Path) -> None:
    input_path = tmp_path / "books_enriched.csv"
    review_path = tmp_path / "books_review.csv"
    report_path = tmp_path / "books_quality_report.json"

    rows: list[dict[str, str]] = [
        {
            "id": "1",
            "titulo": "Libro A",
            "autor_o_autores": "Autor A",
            "editorial": "desconocido",
            "idioma": "ingles",
            "genero": "Programacion",
            "isbn_13": "9781234567890",
            "isbn_10": "",
            "source": "openlibrary",
            "source_id": "/works/OL1W",
            "confidence": "0.95",
            "review_status": "auto_accepted",
            "metadata_source": "google_books",
            "metadata_confidence": "0.90",
            "conflict_notes": "",
            "enriched_at": "2026-03-04T00:00:00+00:00",
        },
        {
            "id": "2",
            "titulo": "Libro B",
            "autor_o_autores": "desconocido",
            "editorial": "desconocido",
            "idioma": "desconocido",
            "genero": "Programacion",
            "isbn_13": "",
            "isbn_10": "",
            "source": "",
            "source_id": "",
            "confidence": "0.20",
            "review_status": "unresolved",
            "metadata_source": "",
            "metadata_confidence": "0.00",
            "conflict_notes": "",
            "enriched_at": "2026-03-04T00:00:00+00:00",
        },
        {
            "id": "3",
            "titulo": "Libro C",
            "autor_o_autores": "Autor C",
            "editorial": "Manning",
            "idioma": "ingles",
            "genero": "Programacion",
            "isbn_13": "9781111111111",
            "isbn_10": "",
            "source": "google_books",
            "source_id": "abc123",
            "confidence": "0.80",
            "review_status": "needs_review",
            "metadata_source": "openlibrary",
            "metadata_confidence": "0.80",
            "conflict_notes": "editorial mismatch",
            "enriched_at": "2026-03-04T00:00:00+00:00",
        },
    ]

    with input_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    total, review_rows = run_phase4(
        input_path=input_path,
        review_output_path=review_path,
        report_output_path=report_path,
    )

    assert total == 3
    assert review_rows == 2

    with review_path.open(newline="", encoding="utf-8") as fh:
        review_data = list(csv.DictReader(fh))
    assert len(review_data) == 2
    assert {row["id"] for row in review_data} == {"2", "3"}

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["total_rows"] == 3
    assert report["review_status_distribution"]["auto_accepted"] == 1
    assert report["review_status_distribution"]["needs_review"] == 1
    assert report["review_status_distribution"]["unresolved"] == 1
    assert report["coverage"]["isbn"] == 0.6667
