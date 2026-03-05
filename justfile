set shell := ["fish", "-c"]

help:
    just --list

lint:
    uv run basedpyright
    uv run ruff check .

test:
    uv run pytest -q

check: lint test
