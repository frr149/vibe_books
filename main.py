from __future__ import annotations

import csv
from pathlib import Path


DEFAULT_SOURCE = Path("data/books.csv")


def main() -> None:
    source = DEFAULT_SOURCE
    if not source.exists():
        raise SystemExit(f"No se encontro la fuente de datos: {source}")

    with source.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    print(f"Fuente de datos: {source}")
    print(f"Libros cargados: {len(rows)}")


if __name__ == "__main__":
    main()
