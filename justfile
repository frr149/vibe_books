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

load-sqlite:
    uv run python -m etl.cli load-sqlite --input data/books_enriched.csv --db-path data/books_catalog.db

api-dev:
    uv run uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
