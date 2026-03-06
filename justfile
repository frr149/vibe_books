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

api-test:
    uv run pytest -q tests/test_api_*.py tests/contract

api-check-links:
    uv run python scripts/api_check_links.py --base-url http://127.0.0.1:8000

export-api-fixtures:
    uv run python scripts/export_api_fixtures.py --db-path data/books_catalog.db --output-dir tests/fixtures/real

doctor-contract:
    uv run pytest -q tests/contract
