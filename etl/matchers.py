from __future__ import annotations

from rapidfuzz import fuzz

from etl.models import MatchScores, NormalizedBook, SourceBook
from etl.normalize import UNKNOWN_VALUE, matching_key


def split_authors(authors: str) -> list[str]:
    if not authors or matching_key(authors) == UNKNOWN_VALUE:
        return []
    return [item.strip() for item in authors.split(";") if item.strip()]


def similarity_ratio(left: str, right: str) -> float:
    left_key = matching_key(left)
    right_key = matching_key(right)
    if not left_key or not right_key:
        return 0.0
    return fuzz.token_set_ratio(left_key, right_key) / 100.0


def authors_overlap(left: str, right: str) -> float:
    left_authors = {matching_key(item) for item in split_authors(left)}
    right_authors = {matching_key(item) for item in split_authors(right)}
    left_authors.discard("")
    right_authors.discard("")
    if not left_authors or not right_authors:
        return 0.0
    intersection = len(left_authors.intersection(right_authors))
    return intersection / max(len(left_authors), len(right_authors))


def language_score(book_language: str, candidate_language: str) -> float:
    left = matching_key(book_language)
    right = matching_key(candidate_language)
    if not left or not right:
        return 0.0
    if left == UNKNOWN_VALUE or right == UNKNOWN_VALUE:
        return 0.5
    if left == right:
        return 1.0
    return 0.0


def publisher_score(book_publisher: str, candidate_publisher: str) -> float:
    left = matching_key(book_publisher)
    right = matching_key(candidate_publisher)
    if not left or not right:
        return 0.0
    if left == UNKNOWN_VALUE or right == UNKNOWN_VALUE:
        return 0.5
    return similarity_ratio(left, right)


def compute_match_scores(book: NormalizedBook, candidate: SourceBook) -> MatchScores:
    title = similarity_ratio(book.titulo, candidate.title)
    authors = max(
        authors_overlap(book.autor_o_autores, candidate.authors),
        similarity_ratio(book.autor_o_autores, candidate.authors),
    )
    language = language_score(book.idioma, candidate.language)
    publisher = publisher_score(book.editorial, candidate.publisher)

    total = (0.55 * title) + (0.25 * authors) + (0.10 * language) + (0.10 * publisher)
    return MatchScores(
        title_score=round(title, 4),
        authors_score=round(authors, 4),
        language_score=round(language, 4),
        publisher_score=round(publisher, 4),
        total_score=round(total, 4),
    )


def classify_review_status(score: float) -> str:
    if score >= 0.90:
        return "auto_accepted"
    if score >= 0.75:
        return "needs_review"
    return "unresolved"

