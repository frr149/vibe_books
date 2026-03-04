from __future__ import annotations

import argparse
from pathlib import Path

from etl.normalize import normalize_csv
from etl.resolve_isbn import resolve_isbn


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CLI de ETL para catalogo de libros.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    normalize_parser = subparsers.add_parser(
        "normalize",
        help="Ejecuta la Fase 1: limpieza y normalizacion de datos base.",
    )
    normalize_parser.add_argument(
        "--input",
        default="data/books.csv",
        help="CSV de entrada (default: data/books.csv).",
    )
    normalize_parser.add_argument(
        "--output",
        default="data/books_normalized.csv",
        help="CSV normalizado de salida (default: data/books_normalized.csv).",
    )

    resolve_parser = subparsers.add_parser(
        "resolve-isbn",
        help="Ejecuta la Fase 2: busca candidatos por titulo/autor y resuelve ISBN.",
    )
    resolve_parser.add_argument(
        "--input",
        default="data/books_normalized.csv",
        help="CSV normalizado de entrada (default: data/books_normalized.csv).",
    )
    resolve_parser.add_argument(
        "--output-candidates",
        default="data/books_candidates.csv",
        help="CSV de candidatos (default: data/books_candidates.csv).",
    )
    resolve_parser.add_argument(
        "--output-resolved",
        default="data/books_isbn_resolved.csv",
        help="CSV con ISBN resuelto (default: data/books_isbn_resolved.csv).",
    )
    resolve_parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.75,
        help="Score minimo para aceptar ISBN (default: 0.75).",
    )
    resolve_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita filas procesadas para pruebas.",
    )
    return parser


def run_normalize(input_file: str, output_file: str) -> int:
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        raise SystemExit(f"No se encontro el archivo de entrada: {input_path}")

    rows, unknown_publishers = normalize_csv(input_path=input_path, output_path=output_path)
    print(f"Fase 1 completada: {rows} filas normalizadas")
    print(f"Editoriales desconocidas: {unknown_publishers}")
    print(f"Salida: {output_path}")
    return 0


def run_resolve_isbn(
    input_file: str,
    output_candidates: str,
    output_resolved: str,
    min_confidence: float,
    limit: int | None,
) -> int:
    input_path = Path(input_file)
    candidates_path = Path(output_candidates)
    resolved_path = Path(output_resolved)

    if not input_path.exists():
        raise SystemExit(f"No se encontro el archivo de entrada: {input_path}")

    rows, resolved = resolve_isbn(
        input_path=input_path,
        candidates_output_path=candidates_path,
        resolved_output_path=resolved_path,
        min_confidence=min_confidence,
        limit=limit,
    )
    print(f"Fase 2 completada: {rows} filas procesadas")
    print(f"ISBN aceptados (score >= {min_confidence:.2f}): {resolved}")
    print(f"Salida candidatos: {candidates_path}")
    print(f"Salida resueltos: {resolved_path}")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "normalize":
        return run_normalize(args.input, args.output)
    if args.command == "resolve-isbn":
        return run_resolve_isbn(
            input_file=args.input,
            output_candidates=args.output_candidates,
            output_resolved=args.output_resolved,
            min_confidence=args.min_confidence,
            limit=args.limit,
        )

    raise SystemExit(f"Comando no soportado: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
