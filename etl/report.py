from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from etl.normalize import UNKNOWN_VALUE, matching_key


def _is_filled(value: str) -> bool:
    key = matching_key(value)
    return bool(key) and key != UNKNOWN_VALUE


def _completion_rate(rows: list[dict[str, str]], field: str) -> float:
    if not rows:
        return 0.0
    filled = sum(1 for row in rows if _is_filled(row.get(field, "")))
    return round(filled / len(rows), 4)


def run_phase4(
    input_path: Path,
    review_output_path: Path,
    report_output_path: Path,
) -> tuple[int, int]:
    with input_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    status_counter = Counter(row.get("review_status", "unresolved") for row in rows)
    review_rows = [
        row
        for row in rows
        if row.get("review_status") in {"needs_review", "unresolved"}
    ]

    review_output_path.parent.mkdir(parents=True, exist_ok=True)
    with review_output_path.open("w", newline="", encoding="utf-8") as fh:
        if rows:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(review_rows)

    total = len(rows)
    accepted = status_counter.get("auto_accepted", 0)
    needs_review = status_counter.get("needs_review", 0)
    unresolved = status_counter.get("unresolved", 0)
    report = {
        "total_rows": total,
        "coverage": {
            "autor_o_autores": _completion_rate(rows, "autor_o_autores"),
            "editorial": _completion_rate(rows, "editorial"),
            "idioma": _completion_rate(rows, "idioma"),
            "genero": _completion_rate(rows, "genero"),
            "isbn": round(
                sum(1 for row in rows if _is_filled(row.get("isbn_13", "")) or _is_filled(row.get("isbn_10", "")))
                / max(total, 1),
                4,
            ),
        },
        "review_status_distribution": dict(status_counter),
        "quality_rates": {
            "auto_accepted": round(accepted / max(total, 1), 4),
            "needs_review": round(needs_review / max(total, 1), 4),
            "unresolved": round(unresolved / max(total, 1), 4),
        },
    }

    report_output_path.parent.mkdir(parents=True, exist_ok=True)
    with report_output_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    return total, len(review_rows)

