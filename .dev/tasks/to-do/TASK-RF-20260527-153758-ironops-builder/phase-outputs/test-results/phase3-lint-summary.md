# Phase 3 Lint Summary

| Command | Exit Code |
|---|---|
| `make dev` (uv pip install -e ".[dev]") | 0 (after creating fresh `.venv` — UV's `VIRTUAL_ENV=/lsiopy` env was broken) |
| `make lint` (ruff check src tests) | 0 |

## Ruff Errors

After two fix passes:
- 4 × N818 "Exception should be named with an Error suffix" — silenced via `pyproject.toml [tool.ruff.lint] ignore = ["N818"]` because the BuilderError subclass names are spec-mandated (SPEC §NFR-7 categorical codes).
- 1 × F541 f-string without placeholders in `publish.py::_build_commit_message` — refactored to remove the bare `f""`.
- 1 × F401 unused `format_failure` import in `cli.py` — removed; the CLI builds the failure summary via `result.summary` (set by `pipeline.run_build`).

## Verdict

**PASS** — `ruff check src tests` exits 0.
