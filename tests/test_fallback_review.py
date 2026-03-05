from __future__ import annotations

import csv
import json
from pathlib import Path

from etl.fallback_review import run_fallback_review


def test_run_fallback_review_applies_overrides_and_regenerates_review(tmp_path: Path) -> None:
    enriched_input = tmp_path / "books_enriched.csv"
    review_input = tmp_path / "books_review.csv"
    candidates_input = tmp_path / "books_candidates.csv"
    overrides_output = tmp_path / "books_manual_overrides.csv"
    enriched_output = tmp_path / "books_enriched_updated.csv"
    review_remaining_output = tmp_path / "books_review_remaining.csv"
    report_output = tmp_path / "books_fallback_report.json"

    enriched_rows: list[dict[str, str]] = [
        {
            "id": "10",
            "titulo": "Higher-Order Perl",
            "autor_o_autores": "Mark Jason Dominus",
            "editorial": "Morgan Kaufmann",
            "idioma": "ingles",
            "genero": "Programacion",
            "isbn_13": "",
            "isbn_10": "",
            "source": "",
            "source_id": "",
            "confidence": "0.0000",
            "review_status": "unresolved",
            "metadata_source": "",
            "metadata_confidence": "0.0000",
            "conflict_notes": "",
            "enriched_at": "2026-03-04T00:00:00+00:00",
        },
        {
            "id": "11",
            "titulo": "Libro sin match",
            "autor_o_autores": "Autor X",
            "editorial": "desconocido",
            "idioma": "ingles",
            "genero": "Programacion",
            "isbn_13": "",
            "isbn_10": "",
            "source": "",
            "source_id": "",
            "confidence": "0.0000",
            "review_status": "unresolved",
            "metadata_source": "",
            "metadata_confidence": "0.0000",
            "conflict_notes": "",
            "enriched_at": "2026-03-04T00:00:00+00:00",
        },
    ]

    review_rows: list[dict[str, str]] = [
        dict(enriched_rows[0]),
        dict(enriched_rows[1]),
    ]

    candidates_rows: list[dict[str, str]] = [
        {
            "input_id": "10",
            "titulo_input": "Higher-Order Perl",
            "autores_input": "Mark Jason Dominus",
            "source": "openlibrary",
            "source_id": "/works/OL123W",
            "titulo_candidato": "Higher-Order Perl",
            "autores_candidato": "Mark Jason Dominus",
            "editorial_candidata": "Morgan Kaufmann",
            "idioma_candidato": "ingles",
            "isbn_13": "9781558607019",
            "isbn_10": "1558607013",
            "title_score": "0.99",
            "authors_score": "0.99",
            "language_score": "1.00",
            "publisher_score": "0.99",
            "score": "0.95",
        },
    ]

    with enriched_input.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(enriched_rows[0].keys()))
        writer.writeheader()
        writer.writerows(enriched_rows)

    with review_input.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(review_rows[0].keys()))
        writer.writeheader()
        writer.writerows(review_rows)

    with candidates_input.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(candidates_rows[0].keys()))
        writer.writeheader()
        writer.writerows(candidates_rows)

    total_rows, resolved_by_fallback, review_remaining = run_fallback_review(
        enriched_input_path=enriched_input,
        review_input_path=review_input,
        candidates_input_path=candidates_input,
        overrides_output_path=overrides_output,
        enriched_output_path=enriched_output,
        review_remaining_output_path=review_remaining_output,
        fallback_report_output_path=report_output,
        min_score=0.88,
        min_title_score=0.90,
        min_authors_score=0.40,
        min_margin=0.03,
        enable_online_discovery=False,
    )

    assert total_rows == 2
    assert resolved_by_fallback == 1
    assert review_remaining == 1

    with overrides_output.open(newline="", encoding="utf-8") as fh:
        overrides = list(csv.DictReader(fh))
    assert len(overrides) == 1
    assert overrides[0]["id"] == "10"
    assert overrides[0]["isbn_13"] == "9781558607019"

    with enriched_output.open(newline="", encoding="utf-8") as fh:
        updated_rows = list(csv.DictReader(fh))
    resolved_row = next(row for row in updated_rows if row["id"] == "10")
    assert resolved_row["review_status"] == "auto_accepted"
    assert resolved_row["isbn_13"] == "9781558607019"

    with review_remaining_output.open(newline="", encoding="utf-8") as fh:
        remaining_rows = list(csv.DictReader(fh))
    assert len(remaining_rows) == 1
    assert remaining_rows[0]["id"] == "11"

    report = json.loads(report_output.read_text(encoding="utf-8"))
    assert report["review_before"] == 2
    assert report["resolved_by_fallback"] == 1
    assert report["review_after"] == 1
