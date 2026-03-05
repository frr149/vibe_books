from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from etl.matchers import classify_review_status, compute_match_scores
from etl.models import CandidateMatch, NormalizedBook, SourceBook
from etl.normalize import UNKNOWN_VALUE, matching_key
from etl.sources.google_books import GoogleBooksSource
from etl.sources.openlibrary import OpenLibrarySource


def _load_normalized_books(input_path: Path) -> list[NormalizedBook]:
    with input_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        books: list[NormalizedBook] = []
        for row in reader:
            books.append(
                NormalizedBook(
                    id=int(row["id"]),
                    titulo=row["titulo"],
                    autor_o_autores=row["autor_o_autores"],
                    editorial=row["editorial"],
                    idioma=row["idioma"],
                    genero=row["genero"],
                    titulo_match=row.get("titulo_match", ""),
                    autores_match=row.get("autores_match", ""),
                    editorial_match=row.get("editorial_match", ""),
                )
            )
    return books


def _first_author(authors: str) -> str:
    if matching_key(authors) == UNKNOWN_VALUE:
        return ""
    parts = [item.strip() for item in authors.split(";") if item.strip()]
    return parts[0] if parts else ""


def _candidate_to_row(candidate: CandidateMatch) -> dict[str, str]:
    return {
        "input_id": str(candidate.input_id),
        "titulo_input": candidate.input_title,
        "autores_input": candidate.input_authors,
        "source": candidate.source,
        "source_id": candidate.source_id,
        "titulo_candidato": candidate.candidate_title,
        "autores_candidato": candidate.candidate_authors,
        "editorial_candidata": candidate.candidate_publisher,
        "idioma_candidato": candidate.candidate_language,
        "isbn_13": candidate.isbn_13,
        "isbn_10": candidate.isbn_10,
        "title_score": f"{candidate.scores.title_score:.4f}",
        "authors_score": f"{candidate.scores.authors_score:.4f}",
        "language_score": f"{candidate.scores.language_score:.4f}",
        "publisher_score": f"{candidate.scores.publisher_score:.4f}",
        "score": f"{candidate.scores.total_score:.4f}",
    }


def _resolved_row(
    book: NormalizedBook,
    best: CandidateMatch | None,
    min_confidence: float,
    enriched_at: str,
) -> dict[str, str]:
    base = {
        "id": str(book.id),
        "titulo": book.titulo,
        "autor_o_autores": book.autor_o_autores,
        "editorial": book.editorial,
        "idioma": book.idioma,
        "genero": book.genero,
        "isbn_13": "",
        "isbn_10": "",
        "source": "",
        "source_id": "",
        "confidence": "0.0000",
        "review_status": "unresolved",
        "enriched_at": enriched_at,
    }

    if not best:
        return base

    status = classify_review_status(best.scores.total_score)
    base["confidence"] = f"{best.scores.total_score:.4f}"
    base["review_status"] = status

    if best.scores.total_score >= min_confidence:
        base["isbn_13"] = best.isbn_13
        base["isbn_10"] = best.isbn_10
        base["source"] = best.source
        base["source_id"] = best.source_id
    return base


def _dedupe_source_candidates(candidates: list[SourceBook]) -> list[SourceBook]:
    unique: dict[tuple[str, str, str, str], SourceBook] = {}
    for item in candidates:
        key = (
            item.source,
            item.source_id,
            item.isbn_13,
            item.isbn_10,
        )
        if key not in unique:
            unique[key] = item
    return list(unique.values())


def resolve_isbn(
    input_path: Path,
    candidates_output_path: Path,
    resolved_output_path: Path,
    min_confidence: float = 0.75,
    limit: int | None = None,
) -> tuple[int, int]:
    books = _load_normalized_books(input_path)
    if limit is not None:
        books = books[:limit]

    openlibrary = OpenLibrarySource()
    google_books = GoogleBooksSource()

    try:
        candidate_rows: list[dict[str, str]] = []
        resolved_rows: list[dict[str, str]] = []
        enriched_at = datetime.now(timezone.utc).isoformat()
        resolved_count = 0

        for book in books:
            author_query = _first_author(book.autor_o_autores)
            raw_candidates: list[SourceBook] = []
            raw_candidates.extend(openlibrary.search(book.titulo, author_query, limit=10))
            raw_candidates.extend(google_books.search(book.titulo, author_query, limit=10))
            source_candidates = _dedupe_source_candidates(raw_candidates)

            matches: list[CandidateMatch] = []
            for source_candidate in source_candidates:
                scores = compute_match_scores(book, source_candidate)
                match = CandidateMatch(
                    input_id=book.id,
                    input_title=book.titulo,
                    input_authors=book.autor_o_autores,
                    source=source_candidate.source,
                    source_id=source_candidate.source_id,
                    candidate_title=source_candidate.title,
                    candidate_authors=source_candidate.authors,
                    candidate_publisher=source_candidate.publisher,
                    candidate_language=source_candidate.language,
                    isbn_13=source_candidate.isbn_13,
                    isbn_10=source_candidate.isbn_10,
                    scores=scores,
                )
                matches.append(match)
                candidate_rows.append(_candidate_to_row(match))

            best_match = None
            if matches:
                best_match = sorted(matches, key=lambda item: item.scores.total_score, reverse=True)[0]
                if best_match.scores.total_score >= min_confidence:
                    resolved_count += 1

            resolved_rows.append(
                _resolved_row(
                    book=book,
                    best=best_match,
                    min_confidence=min_confidence,
                    enriched_at=enriched_at,
                )
            )

        candidates_output_path.parent.mkdir(parents=True, exist_ok=True)
        with candidates_output_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=[
                    "input_id",
                    "titulo_input",
                    "autores_input",
                    "source",
                    "source_id",
                    "titulo_candidato",
                    "autores_candidato",
                    "editorial_candidata",
                    "idioma_candidato",
                    "isbn_13",
                    "isbn_10",
                    "title_score",
                    "authors_score",
                    "language_score",
                    "publisher_score",
                    "score",
                ],
            )
            writer.writeheader()
            writer.writerows(candidate_rows)

        resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
        with resolved_output_path.open("w", newline="", encoding="utf-8") as fh:
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
            writer.writerows(resolved_rows)

        return len(books), resolved_count
    finally:
        openlibrary.close()
        google_books.close()
