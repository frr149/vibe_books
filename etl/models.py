from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NormalizedBook:
    id: int
    titulo: str
    autor_o_autores: str
    editorial: str
    idioma: str
    genero: str
    titulo_match: str
    autores_match: str
    editorial_match: str


@dataclass
class SourceBook:
    source: str
    source_id: str
    title: str
    authors: str
    publisher: str
    language: str
    isbn_13: str
    isbn_10: str


@dataclass
class MatchScores:
    title_score: float
    authors_score: float
    language_score: float
    publisher_score: float
    total_score: float


@dataclass
class CandidateMatch:
    input_id: int
    input_title: str
    input_authors: str
    source: str
    source_id: str
    candidate_title: str
    candidate_authors: str
    candidate_publisher: str
    candidate_language: str
    isbn_13: str
    isbn_10: str
    scores: MatchScores

