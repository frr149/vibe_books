from __future__ import annotations

import argparse
from pathlib import Path

from etl.enrich import enrich_from_isbn
from etl.normalize import normalize_csv
from etl.report import run_phase4
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

    enrich_parser = subparsers.add_parser(
        "enrich",
        help="Ejecuta la Fase 3: enriquece campos faltantes usando ISBN resuelto.",
    )
    enrich_parser.add_argument(
        "--input",
        default="data/books_isbn_resolved.csv",
        help="CSV de entrada con ISBN (default: data/books_isbn_resolved.csv).",
    )
    enrich_parser.add_argument(
        "--output",
        default="data/books_enriched.csv",
        help="CSV enriquecido (default: data/books_enriched.csv).",
    )
    enrich_parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.75,
        help="Score minimo para aceptar rellenos automaticos (default: 0.75).",
    )
    enrich_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita filas procesadas para pruebas.",
    )
    enrich_parser.add_argument(
        "--librario-token",
        default=None,
        help="Token de Librario. Si no se envia, usa LIBRARIO_API_TOKEN.",
    )

    phase4_parser = subparsers.add_parser(
        "phase4",
        help="Ejecuta la Fase 4: genera cola de revision y reporte de calidad.",
    )
    phase4_parser.add_argument(
        "--input",
        default="data/books_enriched.csv",
        help="CSV enriquecido de entrada (default: data/books_enriched.csv).",
    )
    phase4_parser.add_argument(
        "--output-review",
        default="data/books_review.csv",
        help="CSV con filas a revisar (default: data/books_review.csv).",
    )
    phase4_parser.add_argument(
        "--output-report",
        default="data/books_quality_report.json",
        help="Reporte JSON de calidad (default: data/books_quality_report.json).",
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


def run_enrich(
    input_file: str,
    output_file: str,
    min_confidence: float,
    limit: int | None,
    librario_token: str | None,
) -> int:
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        raise SystemExit(f"No se encontro el archivo de entrada: {input_path}")

    rows, filled_fields, conflicts = enrich_from_isbn(
        input_path=input_path,
        output_path=output_path,
        min_confidence=min_confidence,
        limit=limit,
        librario_token=librario_token,
    )
    print(f"Fase 3 completada: {rows} filas procesadas")
    print(f"Campos faltantes completados: {filled_fields}")
    print(f"Conflictos detectados: {conflicts}")
    print(f"Salida enriquecida: {output_path}")
    return 0


def run_review_and_report(
    input_file: str,
    output_review: str,
    output_report: str,
) -> int:
    input_path = Path(input_file)
    review_path = Path(output_review)
    report_path = Path(output_report)

    if not input_path.exists():
        raise SystemExit(f"No se encontro el archivo de entrada: {input_path}")

    total, review_rows = run_phase4(
        input_path=input_path,
        review_output_path=review_path,
        report_output_path=report_path,
    )
    print(f"Fase 4 completada: {total} filas analizadas")
    print(f"Filas en cola de revision: {review_rows}")
    print(f"Salida revision: {review_path}")
    print(f"Salida reporte: {report_path}")
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
    if args.command == "enrich":
        return run_enrich(
            input_file=args.input,
            output_file=args.output,
            min_confidence=args.min_confidence,
            limit=args.limit,
            librario_token=args.librario_token,
        )
    if args.command == "phase4":
        return run_review_and_report(
            input_file=args.input,
            output_review=args.output_review,
            output_report=args.output_report,
        )

    raise SystemExit(f"Comando no soportado: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
