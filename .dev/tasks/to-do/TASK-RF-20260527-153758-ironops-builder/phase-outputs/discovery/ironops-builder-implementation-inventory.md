# IronOps v0.1 Builder — Implementation Inventory

Derived from research/01-file-inventory.md (47 files + 2 directory fixtures, 14-wave build order),
research/02-ironclaude-reference-patterns.md (patterns to ADAPT), research/04-test-and-integration-patterns.md (pytest + subprocess shapes), and research/05-gap-fill-disposition.md (D1-D9 authoritative dispositions). Paths are absolute relative to repo root `<WT>` (the worktree checkout; in the canonical task they are `/config/workspace/IronOps/...`).

## Project Root Files

| Path | Purpose | Build wave |
|---|---|---|
| `<WT>/pyproject.toml` | hatchling build, click+PyYAML runtime, ruff+pytest dev deps, scripts entry `ironops="ironops.cli:main"` | A |
| `<WT>/Makefile` | dev/test/lint/format/build/clean targets via UV | A |
| `<WT>/.gitignore` | __pycache__, .venv, dist, .pytest_cache, .ruff_cache, scratch/, staging/, marketplace-clone/, .coverage, coverage.xml | A |
| `<WT>/.python-version` | single line `3.11` | A |
| `<WT>/README.md` | top-level overview replacing the 36-byte stub | N |

## Spec Amendments

| Path | Amendment | Disposition |
|---|---|---|
| `<WT>/.dev/releases/1.0/0.1/SPEC_IRONOPS_DEVOPS_PLUGIN.md` §NFR-7 | append `PUBLISH_FAILED` as 9th categorical code | D3 |
| `<WT>/.dev/releases/1.0/0.1/SPEC_IRONOPS_DEVOPS_PLUGIN.md` §2.1 + §17 Definitions | builder lives in `src/ironops/` package (not `scripts/build_plugin.py`) | D4 |

## Python Source Modules (`<WT>/src/ironops/`)

| Module | Surface | FRs/NFRs/ACs |
|---|---|---|
| `__init__.py` | `__version__: str = "0.1.0"` | — |
| `errors.py` | `ExitCode(IntEnum)` (11 members, 9 user-visible + SUCCESS=0 + INTERNAL_ERROR=99), `BuilderError` base, 9 subclasses, `format_failure(err) -> str` | NFR-7 (9 codes including PUBLISH_FAILED per D3) |
| `manifest.py` | dataclasses `SourceSpec/ImportSpec/PluginSpec/MarketplaceSpec/Manifest`, `RESERVED_GENERATED_PATHS`, `RESERVED_KINDS_V0_1`, `load_manifest`, schema validators | FR-1, FR-14, FR-15, FR-16; D1 (YAML/PyYAML) |
| `sources.py` | `ClonedSource`, `clone_sources`, `_resolve_default_branch` (ls-remote --symref), `_shallow_clone`, `_resolve_sha`, `_verify_clean_working_tree`, `CLONE_DEPTH=1`, `GIT_TIMEOUT_SECONDS=60` | FR-2, FR-3, NFR-9 |
| `render.py` | `RenderedFile`, `render_to_staging`, `_copy_one_import`, `enforce_co_imports`, `_scan_command_for_skill_refs`, `enforce_path_safety`, `CLAUDE_PLUGIN_ROOT_VAR` | FR-1, FR-3, FR-4, FR-7, FR-8, NFR-1 |
| `metadata.py` | `write_plugin_json`, `write_meta_json`, `write_third_party_licenses`, `write_marketplace_json`, `_resolve_builder_version` | FR-6, FR-10, FR-11, FR-12, FR-13, AC-4, AC-5, AC-6 |
| `validate.py` | `ValidatorResult`, `run_validator`, `_resolve_claude_binary`, `VALIDATOR_TIMEOUT_SECONDS=60` | FR-5, FR-9, NFR-4, NFR-7 |
| `publish.py` | `PublishResult`, `publish_to_marketplace`, `_rsync_staging`, `_commit_and_push`, `_build_commit_message`, `verify_marketplace_unchanged_on_failure`, `MARKETPLACE_PLUGIN_SUBDIR="plugins/ironops-devops"`, `DEFAULT_RSYNC_FLAGS=["-a","--delete"]` | FR-9, FR-10, AC-6, NFR-6 |
| `pipeline.py` | `BuildContext`, `BuildResult`, `run_build`, 8 stage functions `_stage_0_preflight` through `_stage_7_report` | §7 (stages 0..7), §10, FR-9, NFR-2, NFR-7 |
| `cli.py` | flat `@click.group() cli`, `build`/`validate`/`version` subcommands, `main` entry; NO `--allow-dirty` (D5); NO subpackage (D2) | FR-12, AC-1 |

## Test Fixtures (`<WT>/tests/fixtures/`)

- `manifests/good.yaml` — minimal-valid manifest with `{{IRONCLAUDE_SNAPSHOT_PATH}}` placeholder; one agent, one skill dir, one command with `requires:`
- `manifests/bad-schema.yaml` — `schema_version: "999"` (FR-14)
- `manifests/bad-empty-imports.yaml` — `imports: []` (FR-15)
- `manifests/bad-self-overwrite.yaml` — `to: ".claude-plugin/plugin.json"` (FR-16)
- `manifests/bad-orphan-command.yaml` — command without companion skill (FR-4)
- `manifests/bad-path-escape.yaml` — `to: "../../etc/passwd"` (FR-8)
- `manifests/bad-hook-kind.yaml` — `kind: hook-config` (§11 reserved)
- `ironclaude-snapshot/` — minimal hermetic subset of IronClaude (devops-architect.md + system-architect.md agents, sc-troubleshoot-protocol skill dir, troubleshoot.md command, LICENSE, README.md documenting source SHA)

## Unit Tests (`<WT>/tests/unit/`)

| File | Tests | FRs/NFRs/ACs |
|---|---|---|
| `test_errors.py` | exit codes distinct, subclasses set code, format_failure single-line + includes code (parametrized over 9 codes including PUBLISH_FAILED) | NFR-7 |
| `test_manifest.py` | 13 tests: happy path, schema_version negatives ("999","1.0","1.x", int 1), empty imports, missing imports, 3x self-overwrite, hook kind, unknown source id, kebab-case plugin name, raw_sha256 recorded | FR-1, FR-14, FR-15, FR-16 |
| `test_sources.py` | 8 tests: default-branch from ls-remote (NOT main/master via inspect.getsource), depth=1, sha recorded for default/explicit ref/explicit sha, clone failure raises, post-build clean tree, ref+sha mutex | FR-2, FR-3, NFR-9 |
| `test_render.py` | 11 tests: single-file emits one, dir expands, byte-identical (copy2), co-import command-without-skill fails, command-with-skill passes, skill-without-command warns, error names both files, path escape (parametrized), CLAUDE_PLUGIN_ROOT allowed, deterministic ordering | FR-1, FR-4, FR-7, FR-8, NFR-1 |
| `test_metadata.py` | 13 tests: plugin.json omits version, plugin.json keys, meta_json schema_version "1", built_at ISO-8601 UTC, builder_version 40-hex, manifest_sha256 matches, sources/imports fanout, summary counts, THIRD_PARTY_LICENSES references upstream LICENSE, per-file mapping, marketplace.json single plugin + source path, _resolve_builder_version raises on dirty tree | FR-6, FR-10, FR-11, FR-12, FR-13, AC-4, AC-5 |

## Integration Tests (`<WT>/tests/integration/`)

| File | Tests | FRs/NFRs/ACs |
|---|---|---|
| `test_pipeline.py` | 6 tests: dry-run happy path, marketplace push w/ AC-6 commit message, validator failure aborts publish, all four generated files emitted, stage timing logged, deterministic two runs (excluding META.json.built_at) | FR-5, FR-9, AC-1, AC-3, AC-6 |
| `test_atomicity.py` | 5 tests: render/metadata/validate/push failures leave marketplace HEAD unchanged; no partial write on clone failure | FR-9, AC-10 |
| `test_negative.py` | 10 tests: every bad-*.yaml fixture + dirty-tree (monkeypatch) + unresolved-upstream (mock_git_clone) + invalid-plugin-json (tamper between metadata and validate) — assert categorical ExitCode + log artifact + one-line stderr + marketplace unchanged | AC-10, NFR-7 |
| `test_golden_output.py` | 5 tests: golden snapshot matches, file count = summary total_files, agent/skill/command counts match §13. Skip if `manifest.yaml` not yet created. REGEN_GOLDEN=1 env var to bootstrap. | AC-2, §13 |

## CLI Tests (`<WT>/tests/cli/`)

| File | Tests | FRs/NFRs/ACs |
|---|---|---|
| `test_cli.py` | 6 tests: version prints version+SHA, build dry-run exits zero, build bad manifest exits categorical code, no interactive input (input=""), validate passes through exit code, help lists `{build, validate, version}` and NOT `--allow-dirty` | FR-12, AC-1, AC-8 |

Plus `<WT>/tests/test_inventory.md` — FR/NFR/AC → test traceability matrix (AC-8).

## CI Workflows (`<WT>/.github/workflows/`)

| File | Triggers | Steps |
|---|---|---|
| `test.yml` | push/PR to main; matrix Py 3.10/3.11/3.12 fail-fast: false | checkout, setup-python, UV install via verbatim §5.1 snippet, `uv pip install --system -e ".[dev]"`, `make lint`, `uv run pytest --cov=ironops --cov-report=xml` (coverage only on 3.10) |
| `build-publish.yml` | push to main + `schedule cron '0 6 * * *'` + workflow_dispatch; `concurrency: ironops-publish`; `permissions: contents: write` | checkout IronOps + UV install + setup-python 3.11 + `uv pip install --system -e .` + install claude CLI + git user config + checkout marketplace repo via `secrets.IRONOPS_MARKETPLACE_TOKEN` + `ironops build` + on-failure upload validate.log/build.log (retention 30 days) |

## Production Manifest (`<WT>/manifest.yaml`)

- `schema_version: "1"`
- `sources.ironclaude.url: "git@github.com:IronbellyOrg/IronClaude.git"` (default branch resolved at build time per FR-2)
- Imports: 11 agents (kind: agent), 10 skill dirs (kind: skill — includes `sc-cleanup-audit-protocol` + `sc-task-protocol` to satisfy FR-4 co-imports), 7 commands (kind: command — `troubleshoot`, `git`, `cli-portify`, `cleanup-audit`, `task`, `research`, `workflow`) with `requires:` fields where applicable
- `# - { ... prd ... }` commented out per OQ-6 deferral to v0.2
- `plugin.name: "ironops-devops"` (NO `version` per FR-13)
- `marketplace.name: "ironops"` with owner block

## Documentation (`<WT>/docs/`)

| File | Purpose |
|---|---|
| `ARCHITECTURE.md` | 8-stage pipeline overview, module-to-stage mapping, where things live, FR/NFR/AC pointer to SPEC |
| `MANIFEST_AUTHORING.md` | schema reference, kind enum, requires field, full example, pitfalls, NFR-3 enforcement section (D8: <1500 tokens always-on, `claude plugin details ironops-devops` verification) |
| `MARKETPLACE_BOOTSTRAP.md` | OQ-3 resolution: manual `gh repo create`, initial commit, `IRONOPS_MARKETPLACE_TOKEN` PAT, workflow_dispatch verification |
| `CHANGELOG.md` | Keep a Changelog format; [0.1.0] — initial release with 9 categorical codes, 8-stage pipeline, FR-1..FR-16, AC-1..AC-10 |

## Per-Item FR/NFR/AC Traceability

Every FR-1..FR-16, NFR-1..NFR-9, AC-1..AC-10 is referenced in at least one source module + one test file. The `tests/test_inventory.md` file is the authoritative traceability matrix (AC-8).

## Validation Commands

- `make dev` — `uv pip install -e ".[dev]"`
- `make lint` — `uv run ruff check src tests`
- `make format` — `uv run ruff format src tests`
- `uv run pytest -v` — full suite
- `uv run ironops build --manifest manifest.yaml --staging dist/staging --dry-run` — smoke
- `claude plugin validate ./dist/staging` — final validator (skipped if `claude` CLI not in env)

## Build-order summary (14 waves)

A (project root) → B (errors) → C (manifest) → D (sources) → E (render) → F (metadata) → G (validate) → H (publish) → I (pipeline) → J (cli) → K (fixtures) → L (unit tests) → M (integration+CLI tests) → N (CI + manifest.yaml + docs).
