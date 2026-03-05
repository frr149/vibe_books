set shell := ["fish", "-c"]

help:
    just --list

lint:
    uv run basedpyright
    uv run ruff check .

test:
    uv run pytest -q

check: lint test

pipeline:
    uv run python -m etl.cli run --input data/books.csv --output data/books_enriched.csv
