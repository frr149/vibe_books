from __future__ import annotations

import argparse
from pathlib import Path

from etl.normalize import normalize_csv


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


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "normalize":
        return run_normalize(args.input, args.output)

    raise SystemExit(f"Comando no soportado: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())

