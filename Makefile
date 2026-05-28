.PHONY: dev test lint format build clean help

SHELL := /bin/bash

dev:
	uv pip install -e ".[dev]"

test:
	uv run pytest

lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests

build:
	uv run ironops build --manifest manifest.yaml --staging dist/staging --dry-run

clean:
	rm -rf dist/ .pytest_cache/ .ruff_cache/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +

help:
	@echo "dev    - install package + dev deps via UV"
	@echo "test   - run pytest"
	@echo "lint   - ruff check src tests"
	@echo "format - ruff format src tests"
	@echo "build  - smoke build via ironops CLI (--dry-run)"
	@echo "clean  - remove build/cache artifacts"
