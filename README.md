# IronOps

A build-time aggregator for Claude Code plugins. IronOps consumes a YAML
manifest declaring upstream Git repos and per-source file allowlists,
renders a curated plugin tree, validates it via `claude plugin validate`,
and atomically publishes it to a private GitHub marketplace.

## Install

```bash
uv pip install -e .
```

## Usage

```bash
# Dry-run smoke build
ironops build \
  --manifest manifest.yaml \
  --staging dist/staging \
  --dry-run

# Full build + publish
ironops build \
  --manifest manifest.yaml \
  --staging staging/ \
  --marketplace marketplace-clone/

# Ad-hoc validation
ironops validate --plugin-dir dist/staging

# Version + builder SHA
ironops version
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — 8-stage pipeline, module mapping.
- [Manifest authoring](docs/MANIFEST_AUTHORING.md) — schema, kind enum,
  co-import rules, common pitfalls.
- [Marketplace bootstrap](docs/MARKETPLACE_BOOTSTRAP.md) — one-time setup
  for the private marketplace repo.
- [Authoritative spec](.dev/releases/1.0/0.1/SPEC_IRONOPS_DEVOPS_PLUGIN.md)
  — FR-1..FR-16, NFR-1..NFR-9, AC-1..AC-10.
- [Changelog](docs/CHANGELOG.md)

## Contributing

```bash
make dev      # install package + dev deps via UV
make test     # run pytest
make lint     # ruff check src tests
make format   # ruff format src tests
make build    # smoke build via ironops CLI (--dry-run)
```

## License

MIT — see [LICENSE](LICENSE).
