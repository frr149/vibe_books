from __future__ import annotations

import argparse
import time
from pathlib import Path

from etl.covers import fetch_covers
from etl.enrich import enrich_from_isbn
from etl.fallback_review import run_fallback_review
from etl.logging_utils import configure_logging, log_event
from etl.normalize import normalize_csv
from etl.report import run_phase4
from etl.resolve_isbn import resolve_isbn


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CLI de ETL para catalogo de libros.")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Nivel de logging estructurado (default: INFO).",
    )
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

    fallback_parser = subparsers.add_parser(
        "fallback-review",
        help="Ejecuta la Fase 4.5: fallback automatico para casos ambiguos.",
    )
    fallback_parser.add_argument(
        "--input-enriched",
        default="data/books_enriched.csv",
        help="CSV enriquecido de entrada (default: data/books_enriched.csv).",
    )
    fallback_parser.add_argument(
        "--input-review",
        default="data/books_review.csv",
        help="CSV en cola de revision (default: data/books_review.csv).",
    )
    fallback_parser.add_argument(
        "--input-candidates",
        default="data/books_candidates.csv",
        help="CSV de candidatos fase 2 (default: data/books_candidates.csv).",
    )
    fallback_parser.add_argument(
        "--output-overrides",
        default="data/books_manual_overrides.csv",
        help="Overrides aplicados por fallback (default: data/books_manual_overrides.csv).",
    )
    fallback_parser.add_argument(
        "--output-enriched",
        default="data/books_enriched.csv",
        help="CSV enriquecido actualizado (default: data/books_enriched.csv).",
    )
    fallback_parser.add_argument(
        "--output-review-remaining",
        default="data/books_review_remaining.csv",
        help="CSV con revision restante (default: data/books_review_remaining.csv).",
    )
    fallback_parser.add_argument(
        "--output-report",
        default="data/books_fallback_report.json",
        help="Reporte del fallback (default: data/books_fallback_report.json).",
    )
    fallback_parser.add_argument(
        "--min-score",
        type=float,
        default=0.88,
        help="Score minimo para autoaceptar (default: 0.88).",
    )
    fallback_parser.add_argument(
        "--min-title-score",
        type=float,
        default=0.90,
        help="Score minimo de titulo (default: 0.90).",
    )
    fallback_parser.add_argument(
        "--min-authors-score",
        type=float,
        default=0.40,
        help="Score minimo de autores (default: 0.40).",
    )
    fallback_parser.add_argument(
        "--min-margin",
        type=float,
        default=0.03,
        help="Margen minimo entre top-1 y top-2 (default: 0.03).",
    )
    fallback_parser.add_argument(
        "--no-online-discovery",
        action="store_true",
        help="Desactiva busqueda online de candidatos adicionales para unresolved.",
    )

    covers_parser = subparsers.add_parser(
        "fetch-covers",
        help="Ejecuta la fase final: descarga portadas usando ISBN.",
    )
    covers_parser.add_argument(
        "--input",
        default="data/books_enriched.csv",
        help="CSV enriquecido de entrada (default: data/books_enriched.csv).",
    )
    covers_parser.add_argument(
        "--output-enriched",
        default="data/books_enriched.csv",
        help="CSV enriquecido de salida con rutas de portada (default: data/books_enriched.csv).",
    )
    covers_parser.add_argument(
        "--covers-dir",
        default="data/covers",
        help="Directorio donde guardar portadas (default: data/covers).",
    )
    covers_parser.add_argument(
        "--output-manifest",
        default="data/covers_manifest.csv",
        help="CSV manifiesto de descarga (default: data/covers_manifest.csv).",
    )
    covers_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita filas procesadas para pruebas.",
    )
    covers_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Si existe portada local, vuelve a descargarla.",
    )

    run_parser = subparsers.add_parser(
        "run",
        help="Ejecuta el pipeline completo (Fases 1-6) en secuencia.",
    )
    run_parser.add_argument(
        "--input",
        default="data/books.csv",
        help="CSV de entrada original (default: data/books.csv).",
    )
    run_parser.add_argument(
        "--output",
        default="data/books_enriched.csv",
        help="CSV enriquecido final (default: data/books_enriched.csv).",
    )
    run_parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.75,
        help="Score minimo para aceptar ISBN/rellenos (default: 0.75).",
    )
    run_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita filas procesadas para pruebas.",
    )
    run_parser.add_argument(
        "--librario-token",
        default=None,
        help="Token de Librario. Si no se envia, usa LIBRARIO_API_TOKEN.",
    )
    run_parser.add_argument(
        "--min-score",
        type=float,
        default=0.88,
        help="Score minimo fallback (default: 0.88).",
    )
    run_parser.add_argument(
        "--min-title-score",
        type=float,
        default=0.90,
        help="Score minimo de titulo fallback (default: 0.90).",
    )
    run_parser.add_argument(
        "--min-authors-score",
        type=float,
        default=0.40,
        help="Score minimo de autores fallback (default: 0.40).",
    )
    run_parser.add_argument(
        "--min-margin",
        type=float,
        default=0.03,
        help="Margen minimo fallback entre top-1 y top-2 (default: 0.03).",
    )
    run_parser.add_argument(
        "--no-online-discovery",
        action="store_true",
        help="Desactiva busqueda online adicional en fallback.",
    )
    run_parser.add_argument(
        "--overwrite-covers",
        action="store_true",
        help="Si existe portada local, vuelve a descargarla en fase de portadas.",
    )
    return parser


def run_normalize(input_file: str, output_file: str) -> int:
    started = time.perf_counter()
    log_event("normalize", "started", input=input_file, output=output_file)
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        raise SystemExit(f"No se encontro el archivo de entrada: {input_path}")

    rows, unknown_publishers = normalize_csv(input_path=input_path, output_path=output_path)
    print(f"Fase 1 completada: {rows} filas normalizadas")
    print(f"Editoriales desconocidas: {unknown_publishers}")
    print(f"Salida: {output_path}")
    log_event(
        "normalize",
        "completed",
        rows=rows,
        unknown_publishers=unknown_publishers,
        output=str(output_path),
        elapsed_seconds=round(time.perf_counter() - started, 3),
    )
    return 0


def run_resolve_isbn(
    input_file: str,
    output_candidates: str,
    output_resolved: str,
    min_confidence: float,
    limit: int | None,
) -> int:
    started = time.perf_counter()
    log_event(
        "resolve_isbn",
        "started",
        input=input_file,
        output_candidates=output_candidates,
        output_resolved=output_resolved,
        min_confidence=min_confidence,
        limit=limit,
    )
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
    log_event(
        "resolve_isbn",
        "completed",
        rows=rows,
        resolved=resolved,
        output_candidates=str(candidates_path),
        output_resolved=str(resolved_path),
        elapsed_seconds=round(time.perf_counter() - started, 3),
    )
    return 0


def run_enrich(
    input_file: str,
    output_file: str,
    min_confidence: float,
    limit: int | None,
    librario_token: str | None,
) -> int:
    started = time.perf_counter()
    log_event(
        "enrich",
        "started",
        input=input_file,
        output=output_file,
        min_confidence=min_confidence,
        limit=limit,
    )
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
    log_event(
        "enrich",
        "completed",
        rows=rows,
        filled_fields=filled_fields,
        conflicts=conflicts,
        output=str(output_path),
        elapsed_seconds=round(time.perf_counter() - started, 3),
    )
    return 0


def run_review_and_report(
    input_file: str,
    output_review: str,
    output_report: str,
) -> int:
    started = time.perf_counter()
    log_event(
        "phase4",
        "started",
        input=input_file,
        output_review=output_review,
        output_report=output_report,
    )
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
    log_event(
        "phase4",
        "completed",
        total=total,
        review_rows=review_rows,
        output_review=str(review_path),
        output_report=str(report_path),
        elapsed_seconds=round(time.perf_counter() - started, 3),
    )
    return 0


def run_fallback(
    input_enriched: str,
    input_review: str,
    input_candidates: str,
    output_overrides: str,
    output_enriched: str,
    output_review_remaining: str,
    output_report: str,
    min_score: float,
    min_title_score: float,
    min_authors_score: float,
    min_margin: float,
    no_online_discovery: bool,
) -> int:
    started = time.perf_counter()
    log_event(
        "fallback_review",
        "started",
        input_enriched=input_enriched,
        input_review=input_review,
        input_candidates=input_candidates,
        output_enriched=output_enriched,
        output_review_remaining=output_review_remaining,
        output_report=output_report,
    )
    enriched_input_path = Path(input_enriched)
    review_input_path = Path(input_review)
    candidates_input_path = Path(input_candidates)
    overrides_output_path = Path(output_overrides)
    enriched_output_path = Path(output_enriched)
    review_remaining_output_path = Path(output_review_remaining)
    report_output_path = Path(output_report)

    for path in (enriched_input_path, review_input_path, candidates_input_path):
        if not path.exists():
            raise SystemExit(f"No se encontro el archivo de entrada: {path}")

    total_rows, resolved_by_fallback, review_remaining = run_fallback_review(
        enriched_input_path=enriched_input_path,
        review_input_path=review_input_path,
        candidates_input_path=candidates_input_path,
        overrides_output_path=overrides_output_path,
        enriched_output_path=enriched_output_path,
        review_remaining_output_path=review_remaining_output_path,
        fallback_report_output_path=report_output_path,
        min_score=min_score,
        min_title_score=min_title_score,
        min_authors_score=min_authors_score,
        min_margin=min_margin,
        enable_online_discovery=not no_online_discovery,
    )
    print(f"Fase 4.5 completada: {total_rows} filas procesadas")
    print(f"Resueltos por fallback: {resolved_by_fallback}")
    print(f"Pendientes tras fallback: {review_remaining}")
    print(f"Overrides: {overrides_output_path}")
    print(f"CSV actualizado: {enriched_output_path}")
    print(f"Revision restante: {review_remaining_output_path}")
    print(f"Reporte fallback: {report_output_path}")
    log_event(
        "fallback_review",
        "completed",
        total_rows=total_rows,
        resolved_by_fallback=resolved_by_fallback,
        review_remaining=review_remaining,
        output_enriched=str(enriched_output_path),
        output_review_remaining=str(review_remaining_output_path),
        output_report=str(report_output_path),
        elapsed_seconds=round(time.perf_counter() - started, 3),
    )
    return 0


def run_fetch_covers(
    input_file: str,
    output_enriched: str,
    covers_dir: str,
    output_manifest: str,
    limit: int | None,
    overwrite: bool,
) -> int:
    started = time.perf_counter()
    log_event(
        "fetch_covers",
        "started",
        input=input_file,
        output_enriched=output_enriched,
        covers_dir=covers_dir,
        output_manifest=output_manifest,
        limit=limit,
        overwrite=overwrite,
    )
    input_path = Path(input_file)
    output_enriched_path = Path(output_enriched)
    covers_path = Path(covers_dir)
    manifest_path = Path(output_manifest)

    if not input_path.exists():
        raise SystemExit(f"No se encontro el archivo de entrada: {input_path}")

    total_rows, downloaded, skipped, errors = fetch_covers(
        input_path=input_path,
        output_enriched_path=output_enriched_path,
        covers_dir=covers_path,
        manifest_output_path=manifest_path,
        overwrite=overwrite,
        limit=limit,
    )
    print(f"Fase final completada: {total_rows} filas procesadas")
    print(f"Portadas descargadas: {downloaded}")
    print(f"Filas omitidas: {skipped}")
    print(f"Errores de descarga: {errors}")
    print(f"Manifest: {manifest_path}")
    print(f"CSV actualizado: {output_enriched_path}")
    log_event(
        "fetch_covers",
        "completed",
        total_rows=total_rows,
        downloaded=downloaded,
        skipped=skipped,
        errors=errors,
        output_enriched=str(output_enriched_path),
        output_manifest=str(manifest_path),
        elapsed_seconds=round(time.perf_counter() - started, 3),
    )
    return 0


def run_pipeline(
    input_file: str,
    output_file: str,
    min_confidence: float,
    limit: int | None,
    librario_token: str | None,
    min_score: float,
    min_title_score: float,
    min_authors_score: float,
    min_margin: float,
    no_online_discovery: bool,
    overwrite_covers: bool,
) -> int:
    started = time.perf_counter()
    input_path = Path(input_file)
    enriched_output_path = Path(output_file)
    base_dir = enriched_output_path.parent

    if not input_path.exists():
        raise SystemExit(f"No se encontro el archivo de entrada: {input_path}")

    normalized_path = base_dir / "books_normalized.csv"
    candidates_path = base_dir / "books_candidates.csv"
    resolved_path = base_dir / "books_isbn_resolved.csv"
    review_path = base_dir / "books_review.csv"
    quality_report_path = base_dir / "books_quality_report.json"
    overrides_path = base_dir / "books_manual_overrides.csv"
    review_remaining_path = base_dir / "books_review_remaining.csv"
    fallback_report_path = base_dir / "books_fallback_report.json"
    covers_dir = base_dir / "covers"
    covers_manifest_path = base_dir / "covers_manifest.csv"

    log_event(
        "pipeline",
        "started",
        input=str(input_path),
        output=str(enriched_output_path),
        limit=limit,
        min_confidence=min_confidence,
    )

    run_normalize(str(input_path), str(normalized_path))
    run_resolve_isbn(
        input_file=str(normalized_path),
        output_candidates=str(candidates_path),
        output_resolved=str(resolved_path),
        min_confidence=min_confidence,
        limit=limit,
    )
    run_enrich(
        input_file=str(resolved_path),
        output_file=str(enriched_output_path),
        min_confidence=min_confidence,
        limit=limit,
        librario_token=librario_token,
    )
    run_review_and_report(
        input_file=str(enriched_output_path),
        output_review=str(review_path),
        output_report=str(quality_report_path),
    )
    run_fallback(
        input_enriched=str(enriched_output_path),
        input_review=str(review_path),
        input_candidates=str(candidates_path),
        output_overrides=str(overrides_path),
        output_enriched=str(enriched_output_path),
        output_review_remaining=str(review_remaining_path),
        output_report=str(fallback_report_path),
        min_score=min_score,
        min_title_score=min_title_score,
        min_authors_score=min_authors_score,
        min_margin=min_margin,
        no_online_discovery=no_online_discovery,
    )
    run_fetch_covers(
        input_file=str(enriched_output_path),
        output_enriched=str(enriched_output_path),
        covers_dir=str(covers_dir),
        output_manifest=str(covers_manifest_path),
        limit=limit,
        overwrite=overwrite_covers,
    )

    print("Pipeline completo finalizado")
    print(f"Salida final: {enriched_output_path}")
    log_event(
        "pipeline",
        "completed",
        output=str(enriched_output_path),
        covers_manifest=str(covers_manifest_path),
        elapsed_seconds=round(time.perf_counter() - started, 3),
    )
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.log_level)

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
    if args.command == "fallback-review":
        return run_fallback(
            input_enriched=args.input_enriched,
            input_review=args.input_review,
            input_candidates=args.input_candidates,
            output_overrides=args.output_overrides,
            output_enriched=args.output_enriched,
            output_review_remaining=args.output_review_remaining,
            output_report=args.output_report,
            min_score=args.min_score,
            min_title_score=args.min_title_score,
            min_authors_score=args.min_authors_score,
            min_margin=args.min_margin,
            no_online_discovery=args.no_online_discovery,
        )
    if args.command == "fetch-covers":
        return run_fetch_covers(
            input_file=args.input,
            output_enriched=args.output_enriched,
            covers_dir=args.covers_dir,
            output_manifest=args.output_manifest,
            limit=args.limit,
            overwrite=args.overwrite,
        )
    if args.command == "run":
        return run_pipeline(
            input_file=args.input,
            output_file=args.output,
            min_confidence=args.min_confidence,
            limit=args.limit,
            librario_token=args.librario_token,
            min_score=args.min_score,
            min_title_score=args.min_title_score,
            min_authors_score=args.min_authors_score,
            min_margin=args.min_margin,
            no_online_discovery=args.no_online_discovery,
            overwrite_covers=args.overwrite_covers,
        )

    raise SystemExit(f"Comando no soportado: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
