from __future__ import annotations

import csv

from etl.normalize import (
    UNKNOWN_VALUE,
    canonicalize_genre,
    canonicalize_language,
    canonicalize_publisher,
    matching_key,
    normalize_authors,
    normalize_csv,
    normalize_display_text,
    normalize_row,
)


def test_normalize_display_text_limpia_espacios_y_comillas() -> None:
    raw = '  “Deep   Learning — with  Python”  '
    assert normalize_display_text(raw) == "Deep Learning - with Python"


def test_matching_key_elimina_acentos_y_puntuacion() -> None:
    assert matching_key("Introducción: Álgebra, Básica!") == "introduccion algebra basica"


def test_normalize_authors_soporta_separadores_y_deduplica() -> None:
    raw = "harold abelson and gerald jay sussman; Harold Abelson"
    assert normalize_authors(raw) == "Harold Abelson; Gerald Jay Sussman"


def test_normalize_authors_desconocido() -> None:
    assert normalize_authors("desconocido") == UNKNOWN_VALUE


def test_canonicalize_publisher_mapea_alias() -> None:
    assert canonicalize_publisher(" oreilly ") == "O'Reilly"
    assert canonicalize_publisher("w h freeman") == "W. H. Freeman"
    assert canonicalize_publisher("desconocido") == UNKNOWN_VALUE


def test_canonicalize_language_mapea_alias() -> None:
    assert canonicalize_language("EN") == "ingles"
    assert canonicalize_language("Frances") == "frances"
    assert canonicalize_language("desconocido") == UNKNOWN_VALUE


def test_canonicalize_genre_mapea_alias() -> None:
    assert canonicalize_genre("machine learning ai") == "Machine Learning / AI"
    assert canonicalize_genre("Programacion") == "Programacion"
    assert canonicalize_genre("desconocido") == UNKNOWN_VALUE


def test_normalize_row_genera_campos_match() -> None:
    row = {
        "titulo": "  Deep Learning with Python  ",
        "autor_o_autores": "francois chollet",
        "editorial": "oreilly",
        "idioma": "EN",
        "genero": "machine learning ai",
    }
    normalized = normalize_row(7, row)
    assert normalized.id == 7
    assert normalized.titulo == "Deep Learning with Python"
    assert normalized.autor_o_autores == "Francois Chollet"
    assert normalized.editorial == "O'Reilly"
    assert normalized.idioma == "ingles"
    assert normalized.genero == "Machine Learning / AI"
    assert normalized.titulo_match == "deep learning with python"
    assert normalized.autores_match == "francois chollet"
    assert normalized.editorial_match == "o reilly"


def test_normalize_csv_escribe_salida_y_contador(tmp_path) -> None:
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"

    with input_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["autor_o_autores", "titulo", "editorial", "idioma", "genero"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "autor_o_autores": "Jane Doe and John Doe",
                "titulo": "  Intro to Data  ",
                "editorial": "oreilly",
                "idioma": "en",
                "genero": "data science",
            }
        )
        writer.writerow(
            {
                "autor_o_autores": "desconocido",
                "titulo": "Otro libro",
                "editorial": "desconocido",
                "idioma": "es",
                "genero": "programacion",
            }
        )

    rows, unknown_publishers = normalize_csv(input_path=input_path, output_path=output_path)
    assert rows == 2
    assert unknown_publishers == 1

    with output_path.open(newline="", encoding="utf-8") as fh:
        result = list(csv.DictReader(fh))

    assert result[0]["id"] == "1"
    assert result[0]["autor_o_autores"] == "Jane Doe; John Doe"
    assert result[0]["editorial"] == "O'Reilly"
    assert result[1]["editorial"] == UNKNOWN_VALUE
