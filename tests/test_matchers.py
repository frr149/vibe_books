from __future__ import annotations

from etl.matchers import (
    authors_overlap,
    classify_review_status,
    compute_match_scores,
    similarity_ratio,
)
from etl.models import NormalizedBook, SourceBook


def test_similarity_ratio_alto_para_titulos_equivalentes() -> None:
    score = similarity_ratio("Deep Learning with Python", "Deep Learning With Python")
    assert score > 0.95


def test_authors_overlap_detecta_interseccion() -> None:
    left = "Harold Abelson; Gerald Jay Sussman"
    right = "Harold Abelson; Julie Sussman"
    assert authors_overlap(left, right) == 0.5


def test_compute_match_scores_combina_componentes() -> None:
    book = NormalizedBook(
        id=1,
        titulo="Deep Learning with Python",
        autor_o_autores="Francois Chollet",
        editorial="Manning",
        idioma="ingles",
        genero="Machine Learning / AI",
        titulo_match="deep learning with python",
        autores_match="francois chollet",
        editorial_match="manning",
    )
    candidate = SourceBook(
        source="openlibrary",
        source_id="/works/OL123W",
        title="Deep Learning with Python",
        authors="Francois Chollet",
        publisher="Manning",
        language="ingles",
        isbn_13="9781617294433",
        isbn_10="1617294438",
    )
    scores = compute_match_scores(book, candidate)
    assert scores.title_score >= 0.99
    assert scores.authors_score >= 0.99
    assert scores.publisher_score >= 0.99
    assert scores.language_score == 1.0
    assert scores.total_score >= 0.99


def test_classify_review_status() -> None:
    assert classify_review_status(0.91) == "auto_accepted"
    assert classify_review_status(0.80) == "needs_review"
    assert classify_review_status(0.60) == "unresolved"

