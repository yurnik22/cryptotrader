# Contributing

Thanks for helping improve Cryptotrader.

## Development setup

1. Install [uv](https://docs.astral.sh/uv/).
2. Clone the repository and run `uv sync --all-extras`.
3. Copy `config.yaml.example` to `config.yaml` and `.env.example` to `.env` as needed.
4. Run checks: `make lint` (or `uv run ruff check .`, `uv run mypy .`, `uv run pytest`).

## Pull requests

- Keep changes focused; avoid unrelated refactors.
- Add or update tests for behavior you change.
- Run `uv run ruff format .` before pushing.
- Paper trading and the single-snapshot-per-cycle design are core invariants—preserve them.

## Reporting issues

Include Python version, OS, config shape (without secrets), and logs when something fails.
