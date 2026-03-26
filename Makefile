# Cryptotrader — use GNU Make or run equivalent `uv` commands manually on Windows.

.PHONY: install run test lint format precommit

install:
	uv sync --all-extras

run:
	uv run python main.py

test:
	uv run pytest -q

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy .

format:
	uv run ruff format .
	uv run ruff check --fix .

precommit:
	uv run pre-commit run --all-files
