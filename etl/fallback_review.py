from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from rapidfuzz import fuzz

from etl.matchers import compute_match_scores
from etl.models import NormalizedBook, SourceBook
from etl.normalize import (
    UNKNOWN_VALUE,
    canonicalize_language,
    canonicalize_publisher,
    matching_key,
    normalize_authors,
)
from etl.report import run_phase4
from etl.sources.google_books import GoogleBooksSource
from etl.sources.openlibrary import OpenLibrarySource


def _is_valid_isbn10(isbn: str) -> bool:
    if len(isbn) != 10:
        return False
    total = 0
    for index, char in enumerate(isbn):
        if char == "X" and index == 9:
            value = 10
        elif char.isdigit():
            value = int(char)
        else:
            return False
        total += (10 - index) * value
    return total % 11 == 0


def _is_valid_isbn13(isbn: str) -> bool:
    if len(isbn) != 13 or not isbn.isdigit():
        return False
    total = 0
    for index, char in enumerate(isbn[:12]):
        factor = 1 if index % 2 == 0 else 3
        total += factor * int(char)
    check_digit = (10 - (total % 10)) % 10
    return check_digit == int(isbn[-1])


def _clean_isbn(value: str) -> str:
    return "".join(char for char in str(value or "") if char.isdigit() or char.upper() == "X")


def _isbn_is_valid(candidate: dict[str, str]) -> bool:
    isbn13 = _clean_isbn(candidate.get("isbn_13", ""))
    isbn10 = _clean_isbn(candidate.get("isbn_10", ""))
    return (isbn13 and _is_valid_isbn13(isbn13)) or (isbn10 and _is_valid_isbn10(isbn10))


def _publisher_compatible(base_value: str, candidate_value: str) -> bool:
    base_key = matching_key(base_value)
    candidate_key = matching_key(candidate_value)
    if not base_key or base_key == UNKNOWN_VALUE:
        return True
    if not candidate_key or candidate_key == UNKNOWN_VALUE:
        return True
    ratio = fuzz.token_set_ratio(base_key, candidate_key) / 100.0
    return ratio >= 0.25


def _language_compatible(base_value: str, candidate_value: str) -> bool:
    base_key = matching_key(base_value)
    candidate_key = matching_key(candidate_value)
    if not base_key or base_key == UNKNOWN_VALUE:
        return True
    if not candidate_key or candidate_key == UNKNOWN_VALUE:
        return True
    return base_key == candidate_key


def _choose_candidate(
    base_row: dict[str, str],
    candidates: list[dict[str, str]],
    min_score: float,
    min_title_score: float,
    min_authors_score: float,
    min_margin: float,
) -> tuple[dict[str, str] | None, str]:
    if not candidates:
        return None, "sin_candidatos"

    top = candidates[0]
    top_score = float(top["score"])
    title_score = float(top["title_score"])
    authors_score = float(top["authors_score"])

    if top_score < min_score:
        return None, "score_bajo"
    if title_score < min_title_score:
        return None, "titulo_bajo"
    if authors_score < min_authors_score:
        return None, "autores_bajo"
    if not _isbn_is_valid(top):
        return None, "isbn_invalido"
    if not _language_compatible(base_row.get("idioma", ""), top.get("idioma_candidato", "")):
        return None, "idioma_incompatible"
    if not _publisher_compatible(base_row.get("editorial", ""), top.get("editorial_candidata", "")):
        return None, "editorial_incompatible"

    if len(candidates) > 1:
        second = candidates[1]
        second_score = float(second["score"])
        top_isbn = _clean_isbn(top.get("isbn_13", "") or top.get("isbn_10", ""))
        second_isbn = _clean_isbn(second.get("isbn_13", "") or second.get("isbn_10", ""))
        if second_isbn and second_isbn != top_isbn:
            if (top_score - second_score) < min_margin:
                return None, "ambiguous_top2"

    return top, "accepted_rule"


def _first_author(authors: str) -> str:
    if matching_key(authors) == UNKNOWN_VALUE:
        return ""
    parts = [item.strip() for item in authors.split(";") if item.strip()]
    return parts[0] if parts else ""


def _title_variants(title: str) -> list[str]:
    base = title.strip()
    variants = [base]
    if ":" in base:
        variants.append(base.split(":", maxsplit=1)[0].strip())
    if "(" in base and ")" in base:
        variants.append(base.split("(", maxsplit=1)[0].strip())
    # Caso frecuente: subtítulo tras " - ".
    if " - " in base:
        variants.append(base.split(" - ", maxsplit=1)[0].strip())
    # Normalización simple para búsquedas anchas.
    variants.append(base.replace("’", "'"))

    unique: list[str] = []
    seen: set[str] = set()
    for item in variants:
        key = matching_key(item)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _sourcebook_to_candidate(
    input_id: int,
    base_row: dict[str, str],
    source_book: SourceBook,
    score: float,
    title_score: float,
    authors_score: float,
    language_score: float,
    publisher_score: float,
) -> dict[str, str]:
    return {
        "input_id": str(input_id),
        "titulo_input": base_row["titulo"],
        "autores_input": base_row["autor_o_autores"],
        "source": source_book.source,
        "source_id": source_book.source_id,
        "titulo_candidato": source_book.title,
        "autores_candidato": source_book.authors,
        "editorial_candidata": source_book.publisher,
        "idioma_candidato": source_book.language,
        "isbn_13": source_book.isbn_13,
        "isbn_10": source_book.isbn_10,
        "title_score": f"{title_score:.4f}",
        "authors_score": f"{authors_score:.4f}",
        "language_score": f"{language_score:.4f}",
        "publisher_score": f"{publisher_score:.4f}",
        "score": f"{score:.4f}",
    }


def _discover_candidates_online(base_row: dict[str, str], input_id: int) -> list[dict[str, str]]:
    book = NormalizedBook(
        id=input_id,
        titulo=base_row["titulo"],
        autor_o_autores=base_row["autor_o_autores"],
        editorial=base_row["editorial"],
        idioma=base_row["idioma"],
        genero=base_row["genero"],
        titulo_match=matching_key(base_row["titulo"]),
        autores_match=matching_key(base_row["autor_o_autores"]),
        editorial_match=matching_key(base_row["editorial"]),
    )

    first_author = _first_author(base_row["autor_o_autores"])
    author_variants = [first_author, ""]
    title_variants = _title_variants(base_row["titulo"])

    openlibrary = OpenLibrarySource()
    google_books = GoogleBooksSource()
    try:
        collected: list[SourceBook] = []
        for title in title_variants[:3]:
            for author in author_variants:
                collected.extend(openlibrary.search(title=title, author=author, limit=8))
                collected.extend(google_books.search(title=title, author=author, limit=8))
    finally:
        openlibrary.close()
        google_books.close()

    # Deduplicar por fuente+isbn+id
    dedup: dict[tuple[str, str, str, str], SourceBook] = {}
    for item in collected:
        key = (item.source, item.source_id, item.isbn_13, item.isbn_10)
        if key not in dedup:
            dedup[key] = item

    candidates: list[dict[str, str]] = []
    for source_book in dedup.values():
        scores = compute_match_scores(book, source_book)
        candidates.append(
            _sourcebook_to_candidate(
                input_id=input_id,
                base_row=base_row,
                source_book=source_book,
                score=scores.total_score,
                title_score=scores.title_score,
                authors_score=scores.authors_score,
                language_score=scores.language_score,
                publisher_score=scores.publisher_score,
            )
        )
    candidates.sort(key=lambda row: float(row["score"]), reverse=True)
    return candidates


def _apply_override(base_row: dict[str, str], candidate: dict[str, str], reason: str) -> tuple[dict[str, str], dict[str, str]]:
    updated = dict(base_row)
    applied_at = datetime.now(timezone.utc).isoformat()
    score = float(candidate["score"])

    candidate_isbn13 = _clean_isbn(candidate.get("isbn_13", ""))
    candidate_isbn10 = _clean_isbn(candidate.get("isbn_10", ""))
    if candidate_isbn13:
        updated["isbn_13"] = candidate_isbn13
    if candidate_isbn10:
        updated["isbn_10"] = candidate_isbn10

    if matching_key(updated.get("autor_o_autores", "")) == UNKNOWN_VALUE:
        updated["autor_o_autores"] = normalize_authors(candidate.get("autores_candidato", ""))
    if matching_key(updated.get("editorial", "")) == UNKNOWN_VALUE:
        updated["editorial"] = canonicalize_publisher(candidate.get("editorial_candidata", ""))
    if matching_key(updated.get("idioma", "")) == UNKNOWN_VALUE:
        updated["idioma"] = canonicalize_language(candidate.get("idioma_candidato", ""))

    updated["source"] = candidate.get("source", updated.get("source", ""))
    updated["source_id"] = candidate.get("source_id", updated.get("source_id", ""))
    updated["confidence"] = f"{max(float(updated.get('confidence', '0') or 0), score):.4f}"
    updated["review_status"] = "auto_accepted"
    updated["metadata_source"] = "fallback_review"
    updated["metadata_confidence"] = f"{score:.4f}"
    updated["conflict_notes"] = reason
    updated["enriched_at"] = applied_at

    override = {
        "id": updated["id"],
        "decision": "accept",
        "reason": reason,
        "fallback_score": f"{score:.4f}",
        "title_score": candidate["title_score"],
        "authors_score": candidate["authors_score"],
        "language_score": candidate["language_score"],
        "publisher_score": candidate["publisher_score"],
        "isbn_13": updated.get("isbn_13", ""),
        "isbn_10": updated.get("isbn_10", ""),
        "source": updated.get("source", ""),
        "source_id": updated.get("source_id", ""),
        "candidate_title": candidate.get("titulo_candidato", ""),
        "candidate_authors": candidate.get("autores_candidato", ""),
        "candidate_publisher": candidate.get("editorial_candidata", ""),
        "candidate_language": candidate.get("idioma_candidato", ""),
        "applied_at": applied_at,
    }
    return updated, override


def run_fallback_review(
    enriched_input_path: Path,
    review_input_path: Path,
    candidates_input_path: Path,
    overrides_output_path: Path,
    enriched_output_path: Path,
    review_remaining_output_path: Path,
    fallback_report_output_path: Path,
    min_score: float = 0.88,
    min_title_score: float = 0.90,
    min_authors_score: float = 0.40,
    min_margin: float = 0.03,
    enable_online_discovery: bool = True,
) -> tuple[int, int, int]:
    with enriched_input_path.open(newline="", encoding="utf-8") as fh:
        enriched_rows = list(csv.DictReader(fh))
    with review_input_path.open(newline="", encoding="utf-8") as fh:
        review_rows = list(csv.DictReader(fh))
    with candidates_input_path.open(newline="", encoding="utf-8") as fh:
        candidate_rows = list(csv.DictReader(fh))

    candidates_by_id: dict[int, list[dict[str, str]]] = defaultdict(list)
    for candidate in candidate_rows:
        input_id = int(candidate["input_id"])
        candidates_by_id[input_id].append(candidate)
    for input_id in candidates_by_id:
        candidates_by_id[input_id].sort(key=lambda row: float(row["score"]), reverse=True)

    enriched_by_id = {int(row["id"]): dict(row) for row in enriched_rows}
    review_ids = [int(row["id"]) for row in review_rows]

    overrides: list[dict[str, str]] = []
    for review_id in review_ids:
        if review_id not in enriched_by_id:
            continue
        base_row = enriched_by_id[review_id]
        local_candidates = list(candidates_by_id.get(review_id, []))

        # Fallback v2: buscar candidatos online con variantes si no hay suficientes.
        if enable_online_discovery and (not local_candidates or float(local_candidates[0]["score"]) < min_score):
            discovered = _discover_candidates_online(base_row=base_row, input_id=review_id)
            if discovered:
                local_candidates.extend(discovered)
                local_candidates.sort(key=lambda row: float(row["score"]), reverse=True)
                # actualizar pool global para trazabilidad posterior
                candidates_by_id[review_id] = local_candidates

        chosen, reason = _choose_candidate(
            base_row=base_row,
            candidates=local_candidates,
            min_score=min_score,
            min_title_score=min_title_score,
            min_authors_score=min_authors_score,
            min_margin=min_margin,
        )
        if not chosen:
            continue
        updated, override = _apply_override(base_row, chosen, reason=reason)
        enriched_by_id[review_id] = updated
        overrides.append(override)

    updated_enriched_rows = [enriched_by_id[int(row["id"])] for row in enriched_rows]
    enriched_output_path.parent.mkdir(parents=True, exist_ok=True)
    with enriched_output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(updated_enriched_rows[0].keys()))
        writer.writeheader()
        writer.writerows(updated_enriched_rows)

    overrides_output_path.parent.mkdir(parents=True, exist_ok=True)
    with overrides_output_path.open("w", newline="", encoding="utf-8") as fh:
        fieldnames = [
            "id",
            "decision",
            "reason",
            "fallback_score",
            "title_score",
            "authors_score",
            "language_score",
            "publisher_score",
            "isbn_13",
            "isbn_10",
            "source",
            "source_id",
            "candidate_title",
            "candidate_authors",
            "candidate_publisher",
            "candidate_language",
            "applied_at",
        ]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(overrides)

    quality_tmp_path = fallback_report_output_path.parent / "_quality_after_fallback_tmp.json"
    total_rows, remaining_review = run_phase4(
        input_path=enriched_output_path,
        review_output_path=review_remaining_output_path,
        report_output_path=quality_tmp_path,
    )
    quality_after = json.loads(quality_tmp_path.read_text(encoding="utf-8"))
    quality_tmp_path.unlink(missing_ok=True)

    report = {
        "total_rows": total_rows,
        "review_before": len(review_rows),
        "resolved_by_fallback": len(overrides),
        "review_after": remaining_review,
        "fallback_rules": {
            "min_score": min_score,
            "min_title_score": min_title_score,
            "min_authors_score": min_authors_score,
            "min_margin": min_margin,
        },
        "quality_after_fallback": quality_after,
    }
    fallback_report_output_path.parent.mkdir(parents=True, exist_ok=True)
    fallback_report_output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return total_rows, len(overrides), remaining_review
