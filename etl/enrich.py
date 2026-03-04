from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from etl.matchers import classify_review_status, compute_match_scores
from etl.models import MatchScores, NormalizedBook, SourceBook
from etl.normalize import (
    UNKNOWN_VALUE,
    canonicalize_language,
    canonicalize_publisher,
    matching_key,
)
from etl.sources.google_books import GoogleBooksSource
from etl.sources.librario import LibrarioSource
from etl.sources.openlibrary import OpenLibrarySource


def _load_phase2_rows(input_path: Path) -> list[dict[str, str]]:
    with input_path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _book_from_row(row: dict[str, str]) -> NormalizedBook:
    return NormalizedBook(
        id=int(row["id"]),
        titulo=row["titulo"],
        autor_o_autores=row["autor_o_autores"],
        editorial=row["editorial"],
        idioma=row["idioma"],
        genero=row["genero"],
        titulo_match=matching_key(row["titulo"]),
        autores_match=matching_key(row["autor_o_autores"]),
        editorial_match=matching_key(row["editorial"]),
    )


def _isbn_from_row(row: dict[str, str]) -> str:
    isbn_13 = row.get("isbn_13", "").strip()
    isbn_10 = row.get("isbn_10", "").strip()
    return isbn_13 or isbn_10


def _best_metadata_candidate(
    book: NormalizedBook,
    candidates: list[SourceBook],
) -> tuple[SourceBook | None, MatchScores | None]:
    if not candidates:
        return None, None

    best_source = None
    best_scores = None
    best_value = -1.0
    for candidate in candidates:
        scores = compute_match_scores(book, candidate)
        if scores.total_score > best_value:
            best_value = scores.total_score
            best_source = candidate
            best_scores = scores
    return best_source, best_scores


def _merge_field(
    current_value: str,
    candidate_value: str,
    candidate_confidence: float,
    min_confidence: float,
) -> tuple[str, bool]:
    current_key = matching_key(current_value)
    candidate_key = matching_key(candidate_value)
    if not candidate_key or candidate_key == UNKNOWN_VALUE:
        return current_value, False

    if not current_key or current_key == UNKNOWN_VALUE:
        if candidate_confidence >= min_confidence:
            return candidate_value, True
        return current_value, False

    if current_key == candidate_key:
        return current_value, False

    return current_value, False


def _detect_conflict(current_value: str, candidate_value: str, confidence: float) -> bool:
    current_key = matching_key(current_value)
    candidate_key = matching_key(candidate_value)
    if not current_key or current_key == UNKNOWN_VALUE:
        return False
    if not candidate_key or candidate_key == UNKNOWN_VALUE:
        return False
    if current_key == candidate_key:
        return False
    return confidence >= 0.85


def enrich_from_isbn(
    input_path: Path,
    output_path: Path,
    min_confidence: float = 0.75,
    limit: int | None = None,
    librario_token: str | None = None,
) -> tuple[int, int, int]:
    rows = _load_phase2_rows(input_path)
    if limit is not None:
        rows = rows[:limit]

    openlibrary = OpenLibrarySource()
    google_books = GoogleBooksSource()
    librario = LibrarioSource(token=librario_token)

    try:
        enriched_rows: list[dict[str, str]] = []
        filled_fields = 0
        conflicts = 0
        enriched_at = datetime.now(timezone.utc).isoformat()

        for row in rows:
            book = _book_from_row(row)
            isbn = _isbn_from_row(row)
            review_status = row.get("review_status", "unresolved")
            base_confidence = float(row.get("confidence", "0") or 0)

            metadata_candidates: list[SourceBook] = []
            if isbn:
                openlibrary_candidate = openlibrary.fetch_by_isbn(isbn)
                google_candidate = google_books.fetch_by_isbn(isbn)
                librario_candidate = librario.fetch_by_isbn(isbn)
                if openlibrary_candidate:
                    metadata_candidates.append(openlibrary_candidate)
                if google_candidate:
                    metadata_candidates.append(google_candidate)
                if librario_candidate:
                    metadata_candidates.append(librario_candidate)

            best_candidate, best_scores = _best_metadata_candidate(book, metadata_candidates)
            metadata_source = ""
            metadata_confidence = 0.0
            conflict_notes: list[str] = []

            if best_candidate and best_scores:
                metadata_source = best_candidate.source
                metadata_confidence = best_scores.total_score

                new_authors, changed = _merge_field(
                    current_value=row["autor_o_autores"],
                    candidate_value=best_candidate.authors,
                    candidate_confidence=metadata_confidence,
                    min_confidence=min_confidence,
                )
                if changed:
                    row["autor_o_autores"] = new_authors
                    filled_fields += 1

                new_publisher, changed = _merge_field(
                    current_value=row["editorial"],
                    candidate_value=canonicalize_publisher(best_candidate.publisher),
                    candidate_confidence=metadata_confidence,
                    min_confidence=min_confidence,
                )
                if changed:
                    row["editorial"] = new_publisher
                    filled_fields += 1

                new_language, changed = _merge_field(
                    current_value=row["idioma"],
                    candidate_value=canonicalize_language(best_candidate.language),
                    candidate_confidence=metadata_confidence,
                    min_confidence=min_confidence,
                )
                if changed:
                    row["idioma"] = new_language
                    filled_fields += 1

                if _detect_conflict(row["editorial"], best_candidate.publisher, metadata_confidence):
                    conflict_notes.append(
                        f"editorial: base='{row['editorial']}' vs metadata='{best_candidate.publisher}'"
                    )
                if _detect_conflict(row["autor_o_autores"], best_candidate.authors, metadata_confidence):
                    conflict_notes.append(
                        f"autores: base='{row['autor_o_autores']}' vs metadata='{best_candidate.authors}'"
                    )
                if _detect_conflict(row["idioma"], best_candidate.language, metadata_confidence):
                    conflict_notes.append(
                        f"idioma: base='{row['idioma']}' vs metadata='{best_candidate.language}'"
                    )

            if conflict_notes:
                conflicts += 1
                if review_status == "auto_accepted":
                    review_status = "needs_review"

            # Nunca degradar confianza existente.
            confidence = max(base_confidence, metadata_confidence)
            if review_status == "unresolved" and confidence >= 0.75:
                review_status = classify_review_status(confidence)

            enriched_rows.append(
                {
                    "id": row["id"],
                    "titulo": row["titulo"],
                    "autor_o_autores": row["autor_o_autores"],
                    "editorial": row["editorial"],
                    "idioma": row["idioma"],
                    "genero": row["genero"],
                    "isbn_13": row.get("isbn_13", ""),
                    "isbn_10": row.get("isbn_10", ""),
                    "source": row.get("source", ""),
                    "source_id": row.get("source_id", ""),
                    "confidence": f"{confidence:.4f}",
                    "review_status": review_status,
                    "metadata_source": metadata_source,
                    "metadata_confidence": f"{metadata_confidence:.4f}",
                    "conflict_notes": " | ".join(conflict_notes),
                    "enriched_at": enriched_at,
                }
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as fh:
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
                    "metadata_source",
                    "metadata_confidence",
                    "conflict_notes",
                    "enriched_at",
                ],
            )
            writer.writeheader()
            writer.writerows(enriched_rows)

        return len(enriched_rows), filled_fields, conflicts
    finally:
        openlibrary.close()
        google_books.close()
        librario.close()

