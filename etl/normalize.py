from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

UNKNOWN_VALUE = "desconocido"

UNKNOWN_TOKENS = {
    "",
    "-",
    "n/a",
    "na",
    "none",
    "null",
    "unknown",
    "desconocido",
}

PUBLISHER_ALIASES = {
    "addison wesley": "Addison-Wesley",
    "apress": "Apress",
    "baen": "Baen",
    "cambridge": "Cambridge",
    "careercup": "CareerCup",
    "cengage": "Cengage",
    "crc press": "CRC Press",
    "del rey": "Del Rey",
    "dutton": "Dutton",
    "for dummies": "For Dummies",
    "idg books": "IDG Books",
    "le livre de poche": "Le Livre de Poche",
    "manning": "Manning",
    "mcgraw hill": "McGraw-Hill",
    "mit press": "MIT Press",
    "morgan kaufmann": "Morgan Kaufmann",
    "no starch press": "No Starch Press",
    "o reilly": "O'Reilly",
    "oreilly": "O'Reilly",
    "orbit": "Orbit",
    "packt": "Packt",
    "penguin": "Penguin",
    "pocket books": "Pocket Books",
    "pragmatic bookshelf": "Pragmatic Bookshelf",
    "prentice hall": "Prentice Hall",
    "princeton university press": "Princeton University Press",
    "sage": "SAGE",
    "simon schuster": "Simon & Schuster",
    "soa": "SOA",
    "springer": "Springer",
    "tor": "Tor",
    "w h freeman": "W. H. Freeman",
    "wiley": "Wiley",
}

LANGUAGE_ALIASES = {
    "aleman": "aleman",
    "de": "aleman",
    "deutsch": "aleman",
    "es": "espanol",
    "espanol": "espanol",
    "espanol espana": "espanol",
    "fr": "frances",
    "frances": "frances",
    "it": "italiano",
    "italiano": "italiano",
    "en": "ingles",
    "eng": "ingles",
    "english": "ingles",
    "ingles": "ingles",
    "pt": "portugues",
    "portugues": "portugues",
}

GENRE_ALIASES = {
    "biografia": "Biografia",
    "ciencia ficcion": "Ciencia ficcion",
    "computer science": "Computer Science",
    "data engineering": "Data Engineering",
    "data science": "Data Science",
    "diseno ux": "Diseno UX",
    "divulgacion cientifica": "Divulgacion cientifica",
    "divulgacion tecnologica": "Divulgacion tecnologica",
    "edtech": "EdTech",
    "estadistica": "Estadistica",
    "finanzas": "Finanzas",
    "game development": "Game Development",
    "machine learning ai": "Machine Learning / AI",
    "matematicas": "Matematicas",
    "negocio": "Negocio",
    "programacion": "Programacion",
    "sistemas": "Sistemas",
    "software": "Software",
    "web development": "Web Development",
}

CONNECTORS = {"de", "del", "da", "das", "dos", "van", "von", "y", "and", "of", "the"}


@dataclass
class NormalizedRow:
    id: int
    titulo: str
    autor_o_autores: str
    editorial: str
    idioma: str
    genero: str
    titulo_match: str
    autores_match: str
    editorial_match: str


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def compact_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_display_text(text: str) -> str:
    if text is None:
        return ""
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = text.strip().strip('"').strip("'")
    text = compact_spaces(text)
    return text


def matching_key(text: str) -> str:
    text = normalize_display_text(text).lower()
    text = strip_accents(text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return compact_spaces(text)


def is_unknown(text: str) -> bool:
    return matching_key(text) in UNKNOWN_TOKENS


def title_case_name(name: str) -> str:
    words = name.split(" ")
    fixed: list[str] = []
    for idx, word in enumerate(words):
        if not word:
            continue
        lower = word.lower()
        if idx > 0 and lower in CONNECTORS:
            fixed.append(lower)
        else:
            fixed.append(word[0].upper() + word[1:])
    return " ".join(fixed)


def normalize_authors(raw_authors: str) -> str:
    cleaned = normalize_display_text(raw_authors)
    if is_unknown(cleaned):
        return UNKNOWN_VALUE

    parts = re.split(r"\s*(?:;|,|\band\b|\by\b)\s*", cleaned, flags=re.IGNORECASE)
    normalized_parts: list[str] = []
    seen: set[str] = set()
    for part in parts:
        part = normalize_display_text(part)
        if not part or is_unknown(part):
            continue
        part = title_case_name(part)
        key = matching_key(part)
        if not key or key in seen:
            continue
        seen.add(key)
        normalized_parts.append(part)

    if not normalized_parts:
        return UNKNOWN_VALUE
    return "; ".join(normalized_parts)


def canonicalize_publisher(raw_publisher: str) -> str:
    cleaned = normalize_display_text(raw_publisher)
    if is_unknown(cleaned):
        return UNKNOWN_VALUE

    alias_key = matching_key(cleaned)
    if alias_key in PUBLISHER_ALIASES:
        return PUBLISHER_ALIASES[alias_key]
    return cleaned


def canonicalize_language(raw_language: str) -> str:
    cleaned = normalize_display_text(raw_language)
    if is_unknown(cleaned):
        return UNKNOWN_VALUE

    alias_key = matching_key(cleaned)
    return LANGUAGE_ALIASES.get(alias_key, cleaned.lower())


def canonicalize_genre(raw_genre: str) -> str:
    cleaned = normalize_display_text(raw_genre)
    if is_unknown(cleaned):
        return UNKNOWN_VALUE

    alias_key = matching_key(cleaned)
    return GENRE_ALIASES.get(alias_key, cleaned)


def normalize_title(raw_title: str) -> str:
    cleaned = normalize_display_text(raw_title)
    return cleaned or UNKNOWN_VALUE


def normalize_row(index: int, row: dict[str, str]) -> NormalizedRow:
    title = normalize_title(row.get("titulo", ""))
    authors = normalize_authors(row.get("autor_o_autores", ""))
    publisher = canonicalize_publisher(row.get("editorial", ""))
    language = canonicalize_language(row.get("idioma", ""))
    genre = canonicalize_genre(row.get("genero", ""))

    return NormalizedRow(
        id=index,
        titulo=title,
        autor_o_autores=authors,
        editorial=publisher,
        idioma=language,
        genero=genre,
        titulo_match=matching_key(title),
        autores_match=matching_key(authors),
        editorial_match=matching_key(publisher),
    )


def normalize_csv(input_path: Path, output_path: Path) -> tuple[int, int]:
    with input_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = [normalize_row(index, row) for index, row in enumerate(reader, start=1)]

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
                "titulo_match",
                "autores_match",
                "editorial_match",
            ],
        )
        writer.writeheader()
        for item in rows:
            writer.writerow(
                {
                    "id": item.id,
                    "titulo": item.titulo,
                    "autor_o_autores": item.autor_o_autores,
                    "editorial": item.editorial,
                    "idioma": item.idioma,
                    "genero": item.genero,
                    "titulo_match": item.titulo_match,
                    "autores_match": item.autores_match,
                    "editorial_match": item.editorial_match,
                }
            )

    unknown_publishers = sum(1 for item in rows if item.editorial == UNKNOWN_VALUE)
    return len(rows), unknown_publishers

