# Research: File Inventory for IronOps v0.1 Builder
**Topic type:** File Inventory (greenfield)
**Scope:** Enumerate every file to create under /config/workspace/IronOps/
**Status:** Complete
**Date:** 2026-05-27

## Overview

This document enumerates every file that must be created under `/config/workspace/IronOps/` to satisfy v0.1 of the IronOps DevOps Claude Plugin builder per `SPEC_IRONOPS_DEVOPS_PLUGIN.md`. Each entry includes absolute path, purpose, expected key exports/signatures, line-count estimate, spec FR/NFR/AC traceability, internal dependencies, and build-order rationale.

Spec section references: §3 (FR-1..FR-16), §4 (NFR-1..NFR-9), §5 (manifest schema), §6 (META.json schema), §7 (pipeline stages 0..7), §8 (state variable registry), §9 (guard boundary table), §10 (pipeline flow), §12 (AC-1..AC-10), §13 (component shortlist), §14 (test strategy).

**Total file count:** 45 (8 Python modules + 1 package init + 10 unit/integration test files + 1 conftest + 7 manifest fixtures + ironclaude-snapshot tree + 2 CI workflows + 4 docs + pyproject.toml + Makefile + .gitignore + .python-version + manifest.yaml + README.md replacement).

---

## 1. Python Source Files (`src/ironops/`)

In dependency order (modules with no internal deps first).

### 1.1 `/config/workspace/IronOps/src/ironops/__init__.py`

**Purpose:** Package marker for `ironops` Python package; exposes version string.

**Key exports:**
- `__version__: str = "0.1.0"` (module constant)

**Line-count estimate:** ~5 lines (very low).

**Spec FRs/NFRs satisfied:** Structural — supports FR-12 (deterministic headless operation by providing a clean package install target).

**Internal dependencies:** None.

**Build order:** Create first — every other `src/ironops/*.py` module is inside this package.

---

### 1.2 `/config/workspace/IronOps/src/ironops/errors.py`

**Purpose:** Centralized error-code enum and base exception types. All non-zero exits produce one of the categorical NFR-7 codes via a custom exception that the CLI catches and translates to exit codes.

**Key exports:**
- `class ExitCode(IntEnum)` with members: `SUCCESS=0`, `MANIFEST_INVALID=10`, `UNRESOLVED_IMPORT=11`, `CO_IMPORT_MISSING=12`, `VALIDATE_FAILED=13`, `PATH_ESCAPE=14`, `UPSTREAM_CLONE_FAILED=15`, `SELF_OVERWRITE=16`, `BUILDER_DIRTY_TREE=17`, `PUBLISH_FAILED=18`, `INTERNAL_ERROR=99`.
- `class BuilderError(Exception)` — base with `code: ExitCode` and `summary: str` attrs.
- Subclass per categorical code: `ManifestInvalid`, `UnresolvedImport`, `CoImportMissing`, `ValidateFailed`, `PathEscape`, `UpstreamCloneFailed`, `SelfOverwrite`, `BuilderDirtyTree`, `PublishFailed`.
- `def format_failure(err: BuilderError) -> str` — one-line stderr summary (NFR-7 part (a)).

**Line-count estimate:** ~70 lines (low-medium).

**Spec FRs/NFRs satisfied:**
- NFR-7 (failure transparency: stderr summary + categorical code + log)
- FR-12 (meaningful exit codes 0 vs ≠0)
- Used as failure surface for FR-1, FR-2, FR-4, FR-5, FR-8, FR-9, FR-14, FR-15, FR-16.

**Internal dependencies:** None (leaf module).

**Build order:** Create immediately after `__init__.py`. Every other module imports `ExitCode` and one or more exception subclasses.

---

### 1.3 `/config/workspace/IronOps/src/ironops/manifest.py`

**Purpose:** Parse `manifest.yaml`, validate against the schema in spec §5, enforce schema_version, reject empty imports, reject self-overwrite targets.

**Key exports:**
- `@dataclass class SourceSpec` — `id: str`, `url: str`, `ref: str | None`, `sha: str | None`.
- `@dataclass class ImportSpec` — `source: str`, `from_path: str` (`from` is a Python keyword), `to: str`, `kind: Literal["agent","skill","command","template","script","other"]`, `requires: list[str]`.
- `@dataclass class PluginSpec` — `name: str`, `description: str`.
- `@dataclass class MarketplaceSpec` — `name: str`, `owner: dict[str, str]`.
- `@dataclass class Manifest` — `schema_version: str`, `sources: dict[str, SourceSpec]`, `imports: list[ImportSpec]`, `plugin: PluginSpec`, `marketplace: MarketplaceSpec`, `raw_sha256: str` (sha256 of the manifest file bytes, for META.json).
- `RESERVED_GENERATED_PATHS: frozenset[str]` = {`.claude-plugin/plugin.json`, `META.json`, `THIRD_PARTY_LICENSES.md`}.
- `RESERVED_KINDS_V0_1: frozenset[str]` = {`hook-config`, `hook-script`} (must reject in v0.1 per §11).
- `def load_manifest(path: Path) -> Manifest` — reads YAML, validates, returns Manifest; raises `ManifestInvalid` or `SelfOverwrite` on schema violations.
- `def validate_schema_version(raw: dict) -> None` (FR-14).
- `def validate_imports_non_empty(raw: dict) -> None` (FR-15).
- `def validate_no_self_overwrite(imports: list) -> None` (FR-16).

**Line-count estimate:** ~180 lines (medium).

**Spec FRs/NFRs satisfied:**
- FR-1 (manifest-driven; rejects manifests with missing sources/imports)
- FR-14 (schema_version exactly `"1"`, string)
- FR-15 (reject empty imports)
- FR-16 (reject self-overwrite of generated paths)
- §5 schema requirements (kebab-case name, kind enum, requires field)
- §9 guard boundary table rows for schema_version, imports non-empty, import.to not self-overwrite.

**Internal dependencies:** `from ironops.errors import ManifestInvalid, SelfOverwrite, ExitCode`.

**External dependencies:** `PyYAML` (declared in pyproject.toml).

**Build order:** After `errors.py`. Tests in `test_manifest.py` validate this module.

---

### 1.4 `/config/workspace/IronOps/src/ironops/sources.py`

**Purpose:** Shallow-clone each upstream source, resolve default branch programmatically, record resolved SHA per source. Read-only contract on upstream working tree.

**Key exports:**
- `@dataclass class ClonedSource` — `id: str`, `path: Path`, `resolved_ref: str`, `resolved_sha: str`.
- `def clone_sources(manifest: Manifest, scratch_dir: Path) -> dict[str, ClonedSource]` — orchestrator returning mapping `source_id -> ClonedSource`.
- `def _resolve_default_branch(url: str) -> str` — uses `git ls-remote --symref <url> HEAD` to resolve default branch without assuming `main`/`master` (FR-2 A3 — Whittaker Divergence Attack closure).
- `def _shallow_clone(url: str, ref: str, dest: Path) -> None` — invokes `git clone --depth=1 --branch <ref> <url> <dest>`.
- `def _resolve_sha(clone_path: Path) -> str` — `git -C <path> rev-parse HEAD`.
- `def _verify_clean_working_tree(clone_path: Path) -> None` — invariant check (NFR-9), raises if dirty after read operations.
- Constant `CLONE_DEPTH = 1` (shallow clone for NFR-2 budget; risk-15 mitigation).
- Constant `GIT_TIMEOUT_SECONDS = 60`.

**Line-count estimate:** ~150 lines (medium).

**Spec FRs/NFRs satisfied:**
- FR-2 (always-latest mainline; default branch resolution; record SHA regardless of ref override)
- FR-3 (read-only upstream — never writes to clone)
- NFR-9 (post-build clean working tree invariant)
- NFR-2 (shallow clone for build-time budget)
- §7 Stage 1 (CLONE)
- §8 state variable `upstream_clones[src_id]` and `resolved_shas[src_id]`.

**Internal dependencies:** `from ironops.errors import UpstreamCloneFailed`, `from ironops.manifest import Manifest, SourceSpec`.

**External dependencies:** `subprocess` (stdlib); git CLI must be present.

**Build order:** After `manifest.py`. Tests in `test_sources.py` mock subprocess.

---

### 1.5 `/config/workspace/IronOps/src/ironops/render.py`

**Purpose:** Copy files/directories from upstream clones into the staging directory; enforce co-import requirements; enforce path safety on all copied content; expand directory imports and record fanout.

**Key exports:**
- `@dataclass class RenderedFile` — `from_path: str` (upstream-relative), `to_path: str` (plugin-relative), `kind: str`, `source_id: str`.
- `def render_to_staging(manifest: Manifest, clones: dict[str, ClonedSource], staging_dir: Path) -> list[RenderedFile]` — main entry; returns the full fanout list (one entry per emitted file; directory imports expand).
- `def _copy_one_import(imp: ImportSpec, clone: ClonedSource, staging_dir: Path) -> list[RenderedFile]` — handles single-file and directory copies via `shutil.copytree(..., dirs_exist_ok=True)` or `shutil.copy2`.
- `def enforce_co_imports(manifest: Manifest) -> None` — scans command-kind imports for `Skill sc:<x>-protocol` references; raises `CoImportMissing` if companion skill not in imports; warns (logs) if reverse (skill without companion command) (FR-4 A1, A2).
- `def _scan_command_for_skill_refs(content: str) -> set[str]` — regex `Skill\s+(sc[:-][a-z0-9-]+(?:-protocol)?)` against command body.
- `def enforce_path_safety(file_path: Path, plugin_root: Path) -> None` — reads file, scans for absolute paths and `..` segments; allows `${CLAUDE_PLUGIN_ROOT}/...`; raises `PathEscape` on escape (FR-8).
- Constants: `CLAUDE_PLUGIN_ROOT_VAR = "${CLAUDE_PLUGIN_ROOT}"`; `PATH_ESCAPE_PATTERNS` (regex list for absolute paths, `../` segments).

**Line-count estimate:** ~240 lines (medium-high).

**Spec FRs/NFRs satisfied:**
- FR-1 (executes copy per manifest entry; fails on unresolved)
- FR-3 (reads from clone; writes only to staging — never modifies clone)
- FR-4 (co-import enforcement; CRITICAL severity)
- FR-7 (no rewriting of skill/agent content — byte-identical copy via `shutil.copy2`)
- FR-8 (path safety inspection on every copied file)
- §7 Stage 3 (RENDER)
- §9 guards for co-import and path-inside-plugin-root
- §10 fanout (N=26 → M=~150) — must enumerate every emitted file for META.json
- NFR-1 (deterministic; copy ordering must be stable — sort imports by `to` path).

**Internal dependencies:** `from ironops.errors import UnresolvedImport, CoImportMissing, PathEscape`, `from ironops.manifest import Manifest, ImportSpec`, `from ironops.sources import ClonedSource`.

**External dependencies:** `shutil` (stdlib), `re` (stdlib).

**Build order:** After `sources.py`. Tests in `test_render.py` (extensive — co-import positive/negative, path-escape positive/negative).

---

### 1.6 `/config/workspace/IronOps/src/ironops/metadata.py`

**Purpose:** Emit four generated files into staging: `plugin.json`, `META.json`, `THIRD_PARTY_LICENSES.md`, and the parent-level `.claude-plugin/marketplace.json` for the marketplace repo.

**Key exports:**
- `def write_plugin_json(staging_dir: Path, manifest: Manifest) -> Path` — emits `.claude-plugin/plugin.json` with `name`, `description`; explicitly omits `version` (FR-13 A1).
- `def write_meta_json(staging_dir: Path, manifest: Manifest, clones: dict[str, ClonedSource], rendered_files: list[RenderedFile], builder_version: str, built_at: datetime | None = None) -> Path` — emits `META.json` per §6 schema with `schema_version: "1"`, `plugin_name`, `built_at` (ISO-8601 UTC), `builder_version` (IronOps git SHA), `manifest_sha256`, `sources[]` (with per-file `imports[]` fanout), and `summary` (agent/skill/command counts + total_files).
- `def write_third_party_licenses(staging_dir: Path, manifest: Manifest, clones: dict[str, ClonedSource], rendered_files: list[RenderedFile]) -> Path` — emits `THIRD_PARTY_LICENSES.md` with one section per source: repo URL, resolved SHA, upstream LICENSE file copied/referenced, per-file mapping (or per-directory mapping for skills).
- `def write_marketplace_json(marketplace_dir: Path, manifest: Manifest) -> Path` — emits `.claude-plugin/marketplace.json` at the marketplace-repo root listing the single `ironops-devops` plugin with `source: "./plugins/ironops-devops"`, `owner`, `marketplace.name`.
- `def _resolve_builder_version() -> str` — `git -C <IronOps repo root> rev-parse HEAD`; raises `BuilderDirtyTree` if working tree dirty (FR-12 + §7 Stage 0).
- Constants: `META_JSON_SCHEMA_VERSION = "1"`, `PLUGIN_JSON_FILENAME = ".claude-plugin/plugin.json"`, `META_JSON_FILENAME = "META.json"`, `LICENSES_FILENAME = "THIRD_PARTY_LICENSES.md"`, `MARKETPLACE_JSON_PATH = ".claude-plugin/marketplace.json"`.

**Line-count estimate:** ~220 lines (medium-high).

**Spec FRs/NFRs satisfied:**
- FR-6 (META.json provenance with per-file `sources[].imports[]`, `built_at`, `builder_version`)
- FR-10 (marketplace.json generation)
- FR-11 (THIRD_PARTY_LICENSES.md per-source, per-file mapping)
- FR-13 (plugin.json omits `version`)
- §6 META.json schema (exact field shape)
- AC-4 (META.json validates against schema; every file has resolved_sha)
- AC-5 (THIRD_PARTY_LICENSES.md present + references upstream IronClaude license)
- AC-6 (commit message contains builder_version and source SHA — consumed by publish.py).

**Internal dependencies:** `from ironops.errors import BuilderDirtyTree`, `from ironops.manifest import Manifest`, `from ironops.sources import ClonedSource`, `from ironops.render import RenderedFile`.

**External dependencies:** `json`, `hashlib`, `datetime` (stdlib).

**Build order:** After `render.py` (needs `RenderedFile`). Tests in `test_metadata.py`.

---

### 1.7 `/config/workspace/IronOps/src/ironops/validate.py`

**Purpose:** Invoke `claude plugin validate` subprocess against the staging directory; capture stdout/stderr; gate Stage 6 on exit 0.

**Key exports:**
- `@dataclass class ValidatorResult` — `exit_code: int`, `stdout: str`, `stderr: str`, `duration_s: float`.
- `def run_validator(staging_dir: Path, log_dir: Path | None = None) -> ValidatorResult` — invokes `claude plugin validate <staging_dir>`; writes full output to `<log_dir>/validate.log` (NFR-7 part (c)); raises `ValidateFailed` if exit ≠0.
- `def _resolve_claude_binary() -> str` — checks `CLAUDE_BIN` env var; falls back to `which claude`.
- Constant `VALIDATOR_TIMEOUT_SECONDS = 60`.

**Line-count estimate:** ~80 lines (low-medium).

**Spec FRs/NFRs satisfied:**
- FR-5 (validation gate; non-zero abort)
- FR-9 (atomicity gate — validate before publish)
- NFR-4 (zero errors, zero warnings)
- NFR-7 (full log retained; categorical code via `ValidateFailed`)
- §7 Stage 5 (VALIDATE)
- §8 state var `validator_exit_code`.

**Internal dependencies:** `from ironops.errors import ValidateFailed`.

**External dependencies:** `subprocess` (stdlib); `claude` CLI must be installed in CI.

**Build order:** After `metadata.py` (logically — Stage 5 runs after Stage 4). Test in `test_pipeline.py` integration mocks the validator.

---

### 1.8 `/config/workspace/IronOps/src/ironops/publish.py`

**Purpose:** Atomic publish to marketplace repo via `rsync --delete` from staging to marketplace clone, then `git add/commit/push`. No-op if any prior stage failed.

**Key exports:**
- `@dataclass class PublishResult` — `pushed: bool`, `commit_sha: str | None`, `commit_message: str`.
- `def publish_to_marketplace(staging_dir: Path, marketplace_repo: Path, manifest: Manifest, clones: dict[str, ClonedSource], builder_version: str) -> PublishResult` — top-level publisher.
- `def _rsync_staging(staging_dir: Path, marketplace_plugin_dir: Path) -> None` — `rsync -a --delete <staging>/ <marketplace_repo>/plugins/ironops-devops/`.
- `def _commit_and_push(marketplace_repo: Path, message: str) -> str` — `git -C <repo> add -A`, `git commit -m <msg>`, `git push origin <default-branch>`; returns resulting commit SHA.
- `def _build_commit_message(manifest: Manifest, clones: dict[str, ClonedSource], builder_version: str) -> str` — includes builder_version and at least one source SHA (AC-6).
- `def verify_marketplace_unchanged_on_failure(marketplace_repo: Path, pre_build_head: str) -> None` — invariant assertion for FR-9 A2 / §8 `marketplace_repo_head`.
- Constants: `MARKETPLACE_PLUGIN_SUBDIR = "plugins/ironops-devops"`, `DEFAULT_RSYNC_FLAGS = ["-a", "--delete"]`.

**Line-count estimate:** ~140 lines (medium).

**Spec FRs/NFRs satisfied:**
- FR-9 (atomic publish; rsync --delete only on validate success; failure → marketplace HEAD unchanged)
- FR-10 (marketplace.json was emitted by metadata.py; this module commits it alongside the plugin tree)
- AC-6 (commit message format)
- NFR-6 (auditability — every published commit has META.json with verifiable SHAs)
- §7 Stage 6 (PUBLISH)
- §8 state var `marketplace_repo_head`.

**Internal dependencies:** `from ironops.errors import PublishFailed`, `from ironops.manifest import Manifest`, `from ironops.sources import ClonedSource`.

**External dependencies:** `subprocess`, `shutil` (for `rsync` invocation); `rsync` + `git` must be present.

**Build order:** After `metadata.py`. Test in `test_atomicity.py` (mid-pipeline kill leaves marketplace unchanged).

---

### 1.9 `/config/workspace/IronOps/src/ironops/pipeline.py`

**Purpose:** Orchestrator wiring the 8 spec pipeline stages (PREFLIGHT, CLONE, READ MANIFEST, RENDER, WRITE METADATA, VALIDATE, PUBLISH, REPORT) with strict atomicity and stage-boundary error categorization.

**Key exports:**
- `@dataclass class BuildContext` — `manifest_path: Path`, `staging_dir: Path`, `scratch_dir: Path`, `marketplace_repo: Path | None`, `builder_version: str`, `dry_run: bool`, `verbose: bool`, `start_time: datetime`.
- `@dataclass class BuildResult` — `success: bool`, `exit_code: ExitCode`, `summary: dict`, `failure: BuilderError | None`.
- `def run_build(ctx: BuildContext) -> BuildResult` — main entry; runs Stages 0..7 in order, catches `BuilderError`, returns structured result.
- `def _stage_0_preflight(ctx: BuildContext) -> None` — verifies python/git/rsync; verifies IronOps working tree clean (FR-12 → `BuilderDirtyTree`).
- `def _stage_1_clone(ctx: BuildContext, manifest: Manifest) -> dict[str, ClonedSource]`.
- `def _stage_2_read_manifest(ctx: BuildContext) -> Manifest` (returns the parsed Manifest; manifest.py already validates).
- `def _stage_3_render(ctx, manifest, clones) -> list[RenderedFile]`.
- `def _stage_4_write_metadata(ctx, manifest, clones, rendered) -> None`.
- `def _stage_5_validate(ctx) -> ValidatorResult`.
- `def _stage_6_publish(ctx, manifest, clones) -> PublishResult | None` — skipped when `dry_run=True`.
- `def _stage_7_report(ctx, manifest, clones, rendered, validator_result, publish_result) -> str` — emits stdout summary (counts, SHAs, validator output, push status).

**Line-count estimate:** ~220 lines (medium-high).

**Spec FRs/NFRs satisfied:**
- All FRs (orchestrates the modules that implement them)
- §7 (canonical pipeline ordering)
- §8 state variable registry (manages lifecycle of `manifest`, `upstream_clones`, `resolved_shas`, `staging_dir`, `validator_exit_code`, `marketplace_repo_head`)
- §10 pipeline flow diagram
- FR-9 atomicity (try/except across stages; marketplace_repo only touched after Stage 5 passes)
- NFR-2 (wall-clock budget) — wraps stages with timing; warns at 60s soft, fails at 5min hard ceiling
- NFR-7 (failure transparency — every raised `BuilderError` becomes structured stderr + log).

**Internal dependencies:** Imports from every other ironops module:
`from ironops.errors import BuilderError, ExitCode, BuilderDirtyTree`,
`from ironops.manifest import load_manifest, Manifest`,
`from ironops.sources import clone_sources, ClonedSource`,
`from ironops.render import render_to_staging, enforce_co_imports, RenderedFile`,
`from ironops.metadata import write_plugin_json, write_meta_json, write_third_party_licenses, write_marketplace_json, _resolve_builder_version`,
`from ironops.validate import run_validator, ValidatorResult`,
`from ironops.publish import publish_to_marketplace, PublishResult`.

**External dependencies:** `tempfile`, `logging`, `time` (stdlib).

**Build order:** Last among `src/ironops/` modules — depends on all others. Tests in `test_pipeline.py`.

---

### 1.10 `/config/workspace/IronOps/src/ironops/cli.py`

**Purpose:** Click-based CLI entry point exposing `ironops build`, `ironops validate`, `ironops version`.

**Key exports:**
- `@click.group()` `def cli()` — top-level group registered as console_script `ironops`.
- `@cli.command()` `def build(manifest, staging, marketplace, dry_run, verbose)` — invokes `pipeline.run_build`; translates `BuildResult.exit_code` to `sys.exit`.
- `@cli.command()` `def validate(plugin_dir)` — invokes `validate.run_validator` directly (for ad-hoc use).
- `@cli.command()` `def version()` — prints `__version__` plus git SHA.
- `def main()` — entry point function registered in `pyproject.toml` `[project.scripts]`.

**Line-count estimate:** ~120 lines (medium).

**Spec FRs/NFRs satisfied:**
- FR-12 (deterministic headless operation; non-interactive — no `click.prompt`; accepts CLI args + env only)
- NFR-7 (stderr summary on failure; full log path printed)
- AC-1 (CI invokes `ironops build` and gets exit 0 on green).

**Internal dependencies:** `from ironops import __version__`, `from ironops.pipeline import run_build, BuildContext`, `from ironops.errors import ExitCode, format_failure`, `from ironops.validate import run_validator`.

**External dependencies:** `click>=8.0`.

**Build order:** After `pipeline.py`. CLI tests in `tests/cli/test_cli.py` use `click.testing.CliRunner`.

---

## 2. Test Files (`tests/`)

### 2.1 `/config/workspace/IronOps/tests/__init__.py`

**Purpose:** Make `tests/` a package so fixtures resolve consistently. Often empty.

**Line-count estimate:** ~1 line (very low).

**Spec FRs/NFRs satisfied:** Structural support for §14 test strategy.

**Internal dependencies:** None.

**Build order:** Create before any test module.

---

### 2.2 `/config/workspace/IronOps/tests/conftest.py`

**Purpose:** Shared pytest fixtures: `tmp_staging`, `tmp_scratch`, `tmp_marketplace_repo`, `good_manifest`, `ironclaude_snapshot_path`, `mock_git_clone`, `mock_claude_validate`.

**Key exports:**
- `@pytest.fixture def tmp_staging(tmp_path) -> Path`.
- `@pytest.fixture def tmp_scratch(tmp_path) -> Path`.
- `@pytest.fixture def tmp_marketplace_repo(tmp_path) -> Path` — initializes a git repo with an initial commit so push targets exist.
- `@pytest.fixture(scope="session") def ironclaude_snapshot_path() -> Path` — points at `tests/fixtures/ironclaude-snapshot/`.
- `@pytest.fixture def good_manifest(tmp_path, ironclaude_snapshot_path) -> Path` — copies `tests/fixtures/manifests/good.yaml` into tmp with the snapshot path interpolated.
- `@pytest.fixture def mock_git_clone(monkeypatch) -> Callable` — replaces `subprocess.run` for `git clone` / `git ls-remote` with a fake that copies from `ironclaude_snapshot_path`.
- `@pytest.fixture def mock_claude_validate(monkeypatch) -> Callable` — replaces validator subprocess with a controllable mock (returns 0 or 1 per param).

**Line-count estimate:** ~150 lines (medium).

**Spec FRs/NFRs satisfied:** Foundation for §14 test classes (Unit, Integration).

**Internal dependencies:** None (test-only).

**External dependencies:** `pytest`, `subprocess`, `pathlib`.

**Build order:** Before any test file.

---

### 2.3 `/config/workspace/IronOps/tests/unit/__init__.py`

**Purpose:** Empty package marker so pytest auto-marker (`@pytest.mark.unit`) applies via `pytest_collection_modifyitems` if configured.

**Line-count estimate:** ~1 line.

**Build order:** Before any unit test.

---

### 2.4 `/config/workspace/IronOps/tests/unit/test_errors.py`

**Purpose:** Verify `ExitCode` enum values, `BuilderError` subclass `.code` mapping, and `format_failure` one-line output shape.

**Key tests:**
- `test_exit_code_enum_values` — asserts every NFR-7 categorical code has a distinct integer.
- `test_builder_error_subclasses_set_code` — instantiating each subclass yields the expected `ExitCode`.
- `test_format_failure_single_line` — output contains no `\n`, contains code name + summary.
- `test_format_failure_includes_code_string` — easier to grep in CI logs.

**Line-count estimate:** ~60 lines (low).

**Spec FRs/NFRs satisfied:** NFR-7 (categorical codes); AC-8 (every FR has a CI test — this covers the failure-surface tests).

**Internal dependencies:** `from ironops.errors import ExitCode, BuilderError, ManifestInvalid, ...`.

**Build order:** First unit test (errors.py has no internal deps).

---

### 2.5 `/config/workspace/IronOps/tests/unit/test_manifest.py`

**Purpose:** Cover `manifest.py` parser including FR-1, FR-14, FR-15, FR-16 guards. Drives fixtures `good.yaml`, `bad-schema.yaml`, `bad-empty-imports.yaml`, `bad-self-overwrite.yaml`.

**Key tests:**
- `test_load_good_manifest_returns_manifest_dataclass` (FR-1 happy path).
- `test_schema_version_missing_rejected` (FR-14, guard row "Zero/Empty").
- `test_schema_version_999_rejected` (FR-14, guard row "Maximum/Overflow").
- `test_schema_version_dotted_rejected` — `"1.0"` rejected (FR-14, "Sentinel Match").
- `test_schema_version_int_rejected` — `1` (int) rejected, must be string `"1"` (FR-14, "Legitimate Edge Case").
- `test_empty_imports_rejected` (FR-15).
- `test_imports_key_missing_rejected` (FR-15).
- `test_self_overwrite_plugin_json_rejected` (FR-16).
- `test_self_overwrite_meta_json_rejected` (FR-16).
- `test_self_overwrite_licenses_rejected` (FR-16).
- `test_hook_kind_rejected_in_v0_1` — `kind: hook-config` / `kind: hook-script` (§11 reserved).
- `test_unknown_source_id_in_import_rejected` (FR-1 unresolved).
- `test_kebab_case_plugin_name_enforced` (§5).
- `test_manifest_sha256_recorded_in_returned_object` (META.json prerequisite).

**Line-count estimate:** ~200 lines (medium-high).

**Spec FRs/NFRs satisfied:** FR-1, FR-14, FR-15, FR-16; §9 guard boundary rows for schema_version, imports non-empty, self-overwrite.

**Internal dependencies:** `from ironops.manifest import load_manifest, Manifest, ...`, `from ironops.errors import ManifestInvalid, SelfOverwrite`.

**Build order:** After `tests/unit/test_errors.py` (logically); requires manifest fixtures in §3.

---

### 2.6 `/config/workspace/IronOps/tests/unit/test_sources.py`

**Purpose:** Cover `sources.py` — clone, default-branch resolution, SHA recording, read-only invariant.

**Key tests:**
- `test_default_branch_resolves_from_ls_remote` — mock `git ls-remote --symref ... HEAD` returning `ref: refs/heads/develop`; verify `develop` is used, not `main` (FR-2 A3).
- `test_shallow_clone_invoked_with_depth_1` — assert subprocess call args.
- `test_resolved_sha_recorded_for_default_branch` (FR-2 A2).
- `test_resolved_sha_recorded_for_explicit_ref` (FR-2 A2).
- `test_resolved_sha_recorded_for_explicit_sha` (FR-2 A2).
- `test_clone_failure_raises_upstream_clone_failed` (NFR-7 categorical).
- `test_post_build_clean_working_tree` — clones a fixture, verifies `git status` clean (NFR-9 / FR-3 A1).
- `test_ref_and_sha_mutually_exclusive` (§5 schema rule).

**Line-count estimate:** ~180 lines (medium).

**Spec FRs/NFRs satisfied:** FR-2, FR-3, NFR-9.

**Internal dependencies:** `from ironops.sources import ...`, `from ironops.errors import UpstreamCloneFailed`.

**Build order:** After test_manifest.py.

---

### 2.7 `/config/workspace/IronOps/tests/unit/test_render.py`

**Purpose:** Cover `render.py` — co-import enforcement and path-safety guards.

**Key tests:**
- `test_render_single_file_import_emits_one_rendered_file` (FR-1).
- `test_render_directory_import_expands_fanout` (§10 divergence — directory → many files in META.json).
- `test_render_preserves_byte_identical_content` (FR-7 A2 — byte-for-byte compare of source vs staging).
- `test_co_import_command_without_skill_fails` (FR-4 A1).
- `test_co_import_command_with_skill_passes` (FR-4 happy path).
- `test_co_import_skill_without_command_warns_not_fails` (FR-4 A2).
- `test_co_import_error_names_both_files` (FR-4 A1 — error message contains skill name + command file).
- `test_path_escape_absolute_path_rejected` — `/config/workspace/IronClaude/...` in skill (FR-8 A1).
- `test_path_escape_dotdot_rejected` — `../../etc/passwd` (FR-8 guard row "Sentinel Match").
- `test_claude_plugin_root_var_allowed` — `${CLAUDE_PLUGIN_ROOT}/scripts/x.sh` (FR-8 A2).
- `test_render_deterministic_ordering` — same input → identical `list[RenderedFile]` order (NFR-1).

**Line-count estimate:** ~280 lines (high — many guard rows exercised here).

**Spec FRs/NFRs satisfied:** FR-1, FR-4, FR-7, FR-8, NFR-1; §9 guards for co-import and path-inside-plugin-root.

**Internal dependencies:** `from ironops.render import ...`, `from ironops.errors import CoImportMissing, PathEscape, UnresolvedImport`.

**Build order:** After test_sources.py.

---

### 2.8 `/config/workspace/IronOps/tests/unit/test_metadata.py`

**Purpose:** Cover `metadata.py` — META.json schema, plugin.json shape, THIRD_PARTY_LICENSES.md generation, marketplace.json shape.

**Key tests:**
- `test_plugin_json_omits_version_key` (FR-13 A1).
- `test_plugin_json_has_required_keys` — name, description.
- `test_meta_json_schema_version_is_1` (§6).
- `test_meta_json_built_at_is_iso8601_utc` (FR-6 A2).
- `test_meta_json_builder_version_is_git_sha` (FR-6 A2).
- `test_meta_json_manifest_sha256_matches_input` (§6).
- `test_meta_json_sources_imports_enumerates_every_file` (FR-6 A1; §10 fanout).
- `test_meta_json_summary_counts_correct` — agent/skill/command counts match manifest kinds.
- `test_third_party_licenses_references_upstream_license` (FR-11 A1, AC-5).
- `test_third_party_licenses_per_file_or_per_directory_mapping` (FR-11).
- `test_marketplace_json_lists_single_plugin` (FR-10 A1).
- `test_marketplace_json_source_path` — `"./plugins/ironops-devops"` (FR-10).
- `test_resolve_builder_version_fails_on_dirty_tree` (FR-12 / Stage 0).

**Line-count estimate:** ~220 lines (medium-high).

**Spec FRs/NFRs satisfied:** FR-6, FR-10, FR-11, FR-13, FR-12; §6 schema; AC-4, AC-5.

**Internal dependencies:** `from ironops.metadata import ...`, `from ironops.manifest`, `from ironops.sources`, `from ironops.render`, `from ironops.errors import BuilderDirtyTree`.

**Build order:** After test_render.py.

---

### 2.9 `/config/workspace/IronOps/tests/integration/__init__.py`

**Purpose:** Package marker for integration tests.

**Line-count estimate:** ~1 line.

**Build order:** Before any integration test.

---

### 2.10 `/config/workspace/IronOps/tests/integration/test_pipeline.py`

**Purpose:** End-to-end pipeline against the ironclaude-snapshot fixture; small two-file manifest covering all happy-path stages.

**Key tests:**
- `test_full_pipeline_dry_run_against_snapshot` — uses `good.yaml` + snapshot, dry-run=True; asserts exit 0, no marketplace push.
- `test_full_pipeline_with_marketplace_push` — uses `tmp_marketplace_repo`; asserts commit added with expected message format (AC-6).
- `test_pipeline_validator_failure_aborts_publish` — `mock_claude_validate` returns 1; asserts marketplace HEAD unchanged (FR-5, FR-9).
- `test_pipeline_emits_all_four_generated_files` — plugin.json, META.json, THIRD_PARTY_LICENSES.md, marketplace.json all present after dry-run.
- `test_pipeline_stage_timing_logged` — NFR-2 wall-clock budget instrumentation.
- `test_pipeline_deterministic_two_runs_byte_identical` (NFR-1, FR-12 A1) — two runs with same pinned SHAs produce identical staging except META.json.built_at.

**Line-count estimate:** ~240 lines (high).

**Spec FRs/NFRs satisfied:** All FRs (integration), FR-5, FR-9, NFR-1, NFR-2; AC-1, AC-3, AC-6.

**Internal dependencies:** `from ironops.pipeline import run_build, BuildContext`, all sub-modules indirectly.

**Build order:** After all unit tests pass.

---

### 2.11 `/config/workspace/IronOps/tests/integration/test_atomicity.py`

**Purpose:** Verify FR-9 atomic publish — mid-pipeline failure leaves marketplace repo HEAD unchanged.

**Key tests:**
- `test_render_failure_leaves_marketplace_unchanged` — inject path-escape; assert marketplace HEAD == pre-build HEAD.
- `test_metadata_failure_leaves_marketplace_unchanged` — patch `write_meta_json` to raise; assert HEAD unchanged.
- `test_validator_failure_leaves_marketplace_unchanged` — `mock_claude_validate` returns 1; HEAD unchanged.
- `test_push_failure_leaves_marketplace_consistent` — simulate push failure mid-Stage-6; staging dir state acceptable but repo not advanced.
- `test_no_partial_write_on_clone_failure` — `mock_git_clone` raises mid-stage-1; staging dir empty or clean.

**Line-count estimate:** ~160 lines (medium).

**Spec FRs/NFRs satisfied:** FR-9 (both A1 and A2); §7 atomicity; §8 `marketplace_repo_head` invariant; AC-10.

**Internal dependencies:** All ironops modules.

**Build order:** After test_pipeline.py.

---

### 2.12 `/config/workspace/IronOps/tests/integration/test_negative.py`

**Purpose:** Every malformed-manifest fixture must fail fast with the correct categorical exit code (AC-10).

**Key tests:**
- `test_bad_schema_yields_manifest_invalid` (FR-14, exit 10).
- `test_bad_empty_imports_yields_manifest_invalid` (FR-15, exit 10).
- `test_bad_self_overwrite_yields_self_overwrite` (FR-16, exit 16).
- `test_bad_orphan_command_yields_co_import_missing` (FR-4, exit 12).
- `test_bad_path_escape_yields_path_escape` (FR-8, exit 14).
- `test_dirty_ironops_tree_yields_builder_dirty_tree` (FR-12, exit 17).
- `test_unresolved_upstream_yields_upstream_clone_failed` — manifest points at non-existent source URL (FR-2, exit 15).
- `test_invalid_plugin_json_yields_validate_failed` — inject malformed plugin.json before validation (FR-5, exit 13).
- `test_every_failure_writes_to_log_artifact` (NFR-7 part c).
- `test_every_failure_writes_one_line_stderr_summary` (NFR-7 part a).

**Line-count estimate:** ~220 lines (medium-high).

**Spec FRs/NFRs satisfied:** AC-10 (definition of done — fail fast on every malformed-manifest fixture); NFR-7 (failure transparency across all categorical codes).

**Internal dependencies:** All ironops modules.

**Build order:** After test_negative manifest fixtures exist.

---

### 2.13 `/config/workspace/IronOps/tests/integration/test_golden_output.py`

**Purpose:** Snapshot test (AC-2) — run the v0.1 manifest against `ironclaude-snapshot`, diff the rendered staging tree against a committed `tests/fixtures/golden/ironops-devops/` tree.

**Key tests:**
- `test_golden_snapshot_matches_for_v0_1_manifest` — run build, recursively compare staging tree to golden tree (excluding META.json.built_at).
- `test_golden_file_count_matches_summary` — file count in golden tree equals META.json.summary.total_files.
- `test_golden_agent_count_matches_shortlist` — 11 agents per §13.
- `test_golden_skill_count_matches_shortlist` — ~8 skills per §13.
- `test_golden_command_count_matches_shortlist` — ~7 commands per §13.

**Line-count estimate:** ~140 lines (medium).

**Spec FRs/NFRs satisfied:** AC-2 (snapshot test); §13 component shortlist verification; AC-9 (guard boundary coverage report by indirectly running the full v0.1 path).

**Internal dependencies:** All ironops modules.

**Build order:** After test_pipeline.py + golden fixture bootstrap.

---

### 2.14 `/config/workspace/IronOps/tests/cli/__init__.py`

**Purpose:** Package marker for CLI tests.

**Line-count estimate:** ~1 line.

**Build order:** Before any CLI test.

---

### 2.15 `/config/workspace/IronOps/tests/cli/test_cli.py`

**Purpose:** `click.testing.CliRunner` against `ironops build`, `ironops validate`, `ironops version`.

**Key tests:**
- `test_cli_version_command_prints_version_and_sha`.
- `test_cli_build_dry_run_against_good_manifest_exits_zero` (AC-1).
- `test_cli_build_bad_manifest_exits_with_categorical_code` — assert exit code matches `ExitCode.MANIFEST_INVALID`.
- `test_cli_build_no_interactive_input_required` (FR-12 A2 — stdin closed; assert no prompt).
- `test_cli_validate_command_passes_through_validator_exit_code`.
- `test_cli_help_text_lists_all_commands`.

**Line-count estimate:** ~120 lines (medium).

**Spec FRs/NFRs satisfied:** FR-12; AC-1; AC-8 (test inventory).

**Internal dependencies:** `from ironops.cli import cli, main`, `from click.testing import CliRunner`.

**Build order:** After all unit tests and `cli.py`.

---

### 2.16 `/config/workspace/IronOps/tests/test_inventory.md`

**Purpose:** Test-to-FR traceability matrix per AC-8 (definition of done — "All 16 FR-N have a corresponding CI test or assertion").

**Content shape:** Markdown table with columns: FR-ID, Test File, Test Function Name(s), Assertion Summary.

**Line-count estimate:** ~80 lines (low-medium).

**Spec FRs/NFRs satisfied:** AC-8.

**Internal dependencies:** None (documentation).

**Build order:** Last test artifact — written after all test files exist.

---

## 3. Test Fixtures (`tests/fixtures/`)

### 3.1 `/config/workspace/IronOps/tests/fixtures/manifests/good.yaml`

**Purpose:** Minimal valid manifest covering all required fields; references the `ironclaude-snapshot` fixture as its source.

**Content sketch:**
```yaml
schema_version: "1"
sources:
  ironclaude:
    url: "file://{{IRONCLAUDE_SNAPSHOT_PATH}}"
imports:
  - source: ironclaude
    from: "src/superclaude/agents/devops-architect.md"
    to: "agents/devops-architect.md"
    kind: agent
  - source: ironclaude
    from: "src/superclaude/skills/sc-troubleshoot-protocol/"
    to: "skills/sc-troubleshoot-protocol/"
    kind: skill
  - source: ironclaude
    from: "src/superclaude/commands/troubleshoot.md"
    to: "commands/troubleshoot.md"
    kind: command
    requires: ["skills/sc-troubleshoot-protocol/"]
plugin:
  name: "ironops-devops-test"
  description: "Test fixture"
marketplace:
  name: "ironops"
  owner: { name: "Test", email: "test@example.invalid" }
```

**Line-count estimate:** ~25 lines (low).

**Spec FRs/NFRs satisfied:** §5 schema reference.

**Build order:** Before unit tests that load it.

---

### 3.2 `/config/workspace/IronOps/tests/fixtures/manifests/bad-schema.yaml`

**Purpose:** Negative fixture with `schema_version: "999"` for FR-14.

**Line-count estimate:** ~5 lines.

**Spec FRs/NFRs satisfied:** FR-14.

---

### 3.3 `/config/workspace/IronOps/tests/fixtures/manifests/bad-empty-imports.yaml`

**Purpose:** `imports: []` for FR-15.

**Line-count estimate:** ~10 lines.

**Spec FRs/NFRs satisfied:** FR-15.

---

### 3.4 `/config/workspace/IronOps/tests/fixtures/manifests/bad-self-overwrite.yaml`

**Purpose:** `to: ".claude-plugin/plugin.json"` or `to: "META.json"` for FR-16.

**Line-count estimate:** ~15 lines.

**Spec FRs/NFRs satisfied:** FR-16.

---

### 3.5 `/config/workspace/IronOps/tests/fixtures/manifests/bad-orphan-command.yaml`

**Purpose:** Command import referencing `Skill sc:troubleshoot-protocol` but without the skill import for FR-4.

**Line-count estimate:** ~15 lines.

**Spec FRs/NFRs satisfied:** FR-4.

---

### 3.6 `/config/workspace/IronOps/tests/fixtures/manifests/bad-path-escape.yaml`

**Purpose:** `to: "../../etc/passwd"` for FR-8.

**Line-count estimate:** ~10 lines.

**Spec FRs/NFRs satisfied:** FR-8.

---

### 3.7 `/config/workspace/IronOps/tests/fixtures/manifests/bad-hook-kind.yaml`

**Purpose:** `kind: hook-config` reserved per §11 — must reject in v0.1.

**Line-count estimate:** ~10 lines.

**Spec FRs/NFRs satisfied:** §11 (reserved kind values).

---

### 3.8 `/config/workspace/IronOps/tests/fixtures/ironclaude-snapshot/` (directory)

**Purpose:** Hermetic snapshot of a minimal subset of IronClaude paths needed by `good.yaml`. Lets unit + integration tests run without network access.

**Required contents (per §13 v0.1 shortlist, minimal subset for tests):**
- `src/superclaude/agents/devops-architect.md` (or copy from IronClaude)
- `src/superclaude/agents/system-architect.md`
- `src/superclaude/skills/sc-troubleshoot-protocol/SKILL.md` (+ refs/, rules/ as present)
- `src/superclaude/commands/troubleshoot.md`
- `LICENSE` (for FR-11 attribution)
- `.git/` initialized so `git rev-parse HEAD` returns a real SHA in tests

**Line-count estimate:** N/A (directory tree; ~10-20 files, ~500 lines total content).

**Spec FRs/NFRs satisfied:** OQ-5 resolution (snapshot for hermetic tests); supports §14 integration tests.

**Build order:** Bootstrap once via the task's fixture-bootstrap item (pins to an IronClaude HEAD at task execution time).

---

### 3.9 `/config/workspace/IronOps/tests/fixtures/golden/ironops-devops/` (directory)

**Purpose:** Committed snapshot of the EXPECTED rendered plugin tree for the v0.1 manifest against the ironclaude-snapshot. Used by `test_golden_output.py` for AC-2.

**Required contents:**
- `.claude-plugin/plugin.json` (no version)
- `agents/<11 agent files>`
- `skills/<8 skill directories with content>`
- `commands/<7 command files>`
- `META.json` (with `built_at` placeholder — comparison logic ignores this field)
- `THIRD_PARTY_LICENSES.md`

**Line-count estimate:** N/A (directory; ~150 files per §13 expected total).

**Spec FRs/NFRs satisfied:** AC-2 (snapshot test).

**Build order:** Generated once by the first successful build run after `test_pipeline.py` passes; committed.

---

## 4. CI Workflows (`.github/workflows/`)

### 4.1 `/config/workspace/IronOps/.github/workflows/test.yml`

**Purpose:** Run `make lint` + `uv run pytest` on push/PR to `main`. Matrix on Python 3.10/3.11/3.12.

**Key sections:**
- `on:` push to main, pull_request to main.
- `jobs.test.strategy.matrix.python-version: ["3.10", "3.11", "3.12"]`.
- Steps: checkout, install UV, `uv pip install --system -e ".[dev]"`, `make lint`, `uv run pytest --cov=ironops --cov-report=xml`.
- Upload coverage to Codecov (optional).

**Line-count estimate:** ~50 lines (low-medium).

**Spec FRs/NFRs satisfied:** AC-8 (CI test execution), AC-9 (coverage report).

**Internal dependencies:** Reads `pyproject.toml`, `Makefile`.

**Build order:** After `pyproject.toml` and `Makefile` exist.

---

### 4.2 `/config/workspace/IronOps/.github/workflows/build-publish.yml`

**Purpose:** UC-1 — Build, validate, and push the rendered plugin to the marketplace repo. Triggered on push to `main`, scheduled rebuild, and manual `workflow_dispatch`.

**Key sections:**
- `on:` push to main + schedule cron (daily) + workflow_dispatch.
- `concurrency: ironops-publish` (risk-15-mitigation — single in-flight build).
- `permissions: contents: write` for marketplace repo push.
- Steps:
  1. Checkout IronOps.
  2. Install UV + Python 3.11.
  3. `uv pip install --system -e .`.
  4. Install `claude` CLI (or pin a version).
  5. Configure git user for commits.
  6. Checkout marketplace repo into `marketplace-clone/` (using `GITHUB_TOKEN` or deploy key).
  7. `ironops build --manifest manifest.yaml --staging staging/ --marketplace marketplace-clone/`.
  8. On failure: upload `validate.log` + `build.log` as artifacts (30-day retention per NFR-7).
  9. On success: push from `marketplace-clone/` is already done by `publish.py`.

**Line-count estimate:** ~90 lines (medium).

**Spec FRs/NFRs satisfied:** UC-1; AC-1, AC-6; NFR-2 (timing); NFR-7 (log retention).

**Internal dependencies:** Reads `pyproject.toml`, `manifest.yaml`, `Makefile` indirectly.

**Build order:** After `pyproject.toml`, `manifest.yaml`, and `src/ironops/` all exist.

---

## 5. Documentation (`docs/`)

### 5.1 `/config/workspace/IronOps/docs/ARCHITECTURE.md`

**Purpose:** Brief overview of the builder's 8-stage pipeline. Points readers at the authoritative spec for FR/NFR/AC detail.

**Key sections:** Pipeline overview diagram (link to spec §10), module-to-stage mapping table, where things live (src/, scripts/, manifest.yaml).

**Line-count estimate:** ~80 lines (low-medium).

**Spec FRs/NFRs satisfied:** Documentation hygiene; AC-7 onboarding.

**Build order:** After src/ironops/ modules exist (so doc can reference them accurately).

---

### 5.2 `/config/workspace/IronOps/docs/MANIFEST_AUTHORING.md`

**Purpose:** UC-2 (release engineer adds/removes manifest entries). How to write/edit `manifest.yaml`.

**Key sections:** schema reference, kind enum, requires field, full example, common pitfalls (self-overwrite, orphan command, hook-kind reserved).

**Line-count estimate:** ~120 lines (medium).

**Spec FRs/NFRs satisfied:** UC-2 documentation; §5 schema reference.

**Build order:** After manifest.py exists.

---

### 5.3 `/config/workspace/IronOps/docs/MARKETPLACE_BOOTSTRAP.md`

**Purpose:** OQ-3 — how to manually create `IronbellyOrg/ironops-marketplace` repo, push the first commit, configure CI secrets (`GITHUB_TOKEN` or deploy key).

**Key sections:** `gh repo create`, initial commit, secret configuration in IronOps repo, verifying first build pushes successfully.

**Line-count estimate:** ~70 lines (low-medium).

**Spec FRs/NFRs satisfied:** OQ-3 resolution; UC-1 prerequisite.

**Build order:** Anytime after CI workflow exists.

---

### 5.4 `/config/workspace/IronOps/docs/CHANGELOG.md`

**Purpose:** Track schema_version bumps (NFR-8); record breaking changes per major bump.

**Initial content:** Header + "## [Unreleased]" + "## [0.1.0] — initial release" with schema_version="1" notes.

**Line-count estimate:** ~30 lines (low).

**Spec FRs/NFRs satisfied:** NFR-8 (schema backwards-compat); Risk-15 (validator pinning notes).

**Build order:** Last doc.

---

## 6. Project Root Files

### 6.1 `/config/workspace/IronOps/pyproject.toml`

**Purpose:** Package metadata, build system (hatchling), dependencies, ruff config, pytest config, console_scripts.

**Key sections:**
- `[project]` — `name = "ironops"`, `version = "0.1.0"`, `requires-python = ">=3.10"`.
- `[project.dependencies]` — `click>=8.0`, `PyYAML>=6.0`.
- `[project.optional-dependencies]` — `dev = ["pytest>=7", "pytest-cov", "ruff", "pyyaml-types-stub"]` (last is illustrative).
- `[project.scripts]` — `ironops = "ironops.cli:main"`.
- `[build-system]` — `requires = ["hatchling"]`, `build-backend = "hatchling.build"`.
- `[tool.ruff]` — line-length 100, target-version py310.
- `[tool.pytest.ini_options]` — `testpaths = ["tests"]`, markers, cov options.

**Line-count estimate:** ~80 lines (low-medium).

**Spec FRs/NFRs satisfied:** FR-12 (deterministic install target); NFR-1 (pinned Python version range).

**Internal dependencies:** None (defines the project).

**Build order:** Very first — required before `make dev` can install anything.

---

### 6.2 `/config/workspace/IronOps/Makefile`

**Purpose:** Convenience targets: `dev`, `lint`, `format`, `test`, `build`, `clean`.

**Key targets:**
- `dev:` — `uv pip install --system -e ".[dev]"`.
- `lint:` — `uv run ruff check src tests`.
- `format:` — `uv run ruff format src tests`.
- `test:` — `uv run pytest`.
- `build:` — `ironops build --manifest manifest.yaml --staging dist/staging --dry-run`.
- `clean:` — remove `dist/`, `.pytest_cache/`, `__pycache__/`, `.ruff_cache/`.

**Line-count estimate:** ~30 lines (low).

**Spec FRs/NFRs satisfied:** Convention compliance; supports AC-1.

**Internal dependencies:** Reads `pyproject.toml`, invokes `ironops` console_script.

**Build order:** After pyproject.toml.

---

### 6.3 `/config/workspace/IronOps/.gitignore`

**Purpose:** Ignore build artifacts, venvs, scratch dirs.

**Key entries:** `__pycache__/`, `*.pyc`, `.venv/`, `dist/`, `.pytest_cache/`, `.ruff_cache/`, `*.egg-info/`, `scratch/`, `staging/`, `marketplace-clone/`, `.coverage`, `coverage.xml`.

**Line-count estimate:** ~25 lines (low).

**Spec FRs/NFRs satisfied:** Hygiene.

**Build order:** Very first (alongside pyproject.toml).

---

### 6.4 `/config/workspace/IronOps/.python-version`

**Purpose:** Pyenv/asdf hint for `3.11` (matches CI matrix center).

**Content:** `3.11`.

**Line-count estimate:** 1 line.

**Spec FRs/NFRs satisfied:** NFR-1 (reproducible runtime).

**Build order:** With other root files.

---

### 6.5 `/config/workspace/IronOps/manifest.yaml`

**Purpose:** The v0.1 production manifest declaring IronClaude as the single source and listing the §13 component shortlist.

**Key entries (per §13):**
- 11 agent imports (devops-architect, system-architect, security-engineer, root-cause-analyst, performance-engineer, backend-architect, quality-engineer, pm-agent, self-review, technical-writer, requirements-analyst).
- 8 skill directory imports (sc-troubleshoot-protocol, sc-crash-recovery, sc-cli-portify-protocol, task, task-builder, tech-research, tdd, tech-reference).
- 7 command imports each with `requires:` pointing at companion skill (troubleshoot, git, cli-portify, cleanup-audit, task, research, workflow).
- `plugin.name: "ironops-devops"`, `marketplace.name: "ironops"`, marketplace owner block.
- `prd` skill **commented out** with TODO note per OQ-6.

**Line-count estimate:** ~140 lines (medium — 26 imports + frontmatter).

**Spec FRs/NFRs satisfied:** §5 schema; §13 component shortlist; FR-1 (source of truth for build); UC-2.

**Internal dependencies:** None (manifest is input).

**Build order:** After manifest.py exists (so schema is locked) and before CI workflow runs the build.

---

### 6.6 `/config/workspace/IronOps/README.md` (replacement)

**Purpose:** Top-level project README. Replaces existing 36-byte stub with builder usage, install, links to docs/spec.

**Key sections:** What IronOps is, install (`uv pip install -e .`), usage (`ironops build`, `ironops validate`), link to ARCHITECTURE.md and SPEC.

**Line-count estimate:** ~80 lines (low-medium).

**Spec FRs/NFRs satisfied:** Onboarding (AC-7 prerequisite).

**Build order:** Late — after most modules and docs exist.

---

## 7. Initial `manifest.yaml` Content Sketch

The v0.1 manifest in §6.5 above expanded per §13:

```yaml
schema_version: "1"

sources:
  ironclaude:
    url: "git@github.com:IronbellyOrg/IronClaude.git"
    # ref unset → builder resolves default branch at build time per FR-2

imports:
  # ---- Agents (11) — §13 shortlist ----
  - { source: ironclaude, from: "src/superclaude/agents/devops-architect.md",        to: "agents/devops-architect.md",        kind: agent }
  - { source: ironclaude, from: "src/superclaude/agents/system-architect.md",         to: "agents/system-architect.md",        kind: agent }
  - { source: ironclaude, from: "src/superclaude/agents/security-engineer.md",        to: "agents/security-engineer.md",       kind: agent }
  - { source: ironclaude, from: "src/superclaude/agents/root-cause-analyst.md",       to: "agents/root-cause-analyst.md",      kind: agent }
  - { source: ironclaude, from: "src/superclaude/agents/performance-engineer.md",     to: "agents/performance-engineer.md",    kind: agent }
  - { source: ironclaude, from: "src/superclaude/agents/backend-architect.md",        to: "agents/backend-architect.md",       kind: agent }
  - { source: ironclaude, from: "src/superclaude/agents/quality-engineer.md",         to: "agents/quality-engineer.md",        kind: agent }
  - { source: ironclaude, from: "src/superclaude/agents/pm-agent.md",                 to: "agents/pm-agent.md",                kind: agent }
  - { source: ironclaude, from: "src/superclaude/agents/self-review.md",              to: "agents/self-review.md",             kind: agent }
  - { source: ironclaude, from: "src/superclaude/agents/technical-writer.md",         to: "agents/technical-writer.md",        kind: agent }
  - { source: ironclaude, from: "src/superclaude/agents/requirements-analyst.md",     to: "agents/requirements-analyst.md",    kind: agent }

  # ---- Skills (8) — directory imports; §13 shortlist ----
  - { source: ironclaude, from: "src/superclaude/skills/sc-troubleshoot-protocol/",   to: "skills/sc-troubleshoot-protocol/",   kind: skill }
  - { source: ironclaude, from: "src/superclaude/skills/sc-crash-recovery/",          to: "skills/sc-crash-recovery/",          kind: skill }
  - { source: ironclaude, from: "src/superclaude/skills/sc-cli-portify-protocol/",    to: "skills/sc-cli-portify-protocol/",    kind: skill }
  - { source: ironclaude, from: "src/superclaude/skills/task/",                       to: "skills/task/",                       kind: skill }
  - { source: ironclaude, from: "src/superclaude/skills/task-builder/",               to: "skills/task-builder/",               kind: skill }
  - { source: ironclaude, from: "src/superclaude/skills/tech-research/",              to: "skills/tech-research/",              kind: skill }
  - { source: ironclaude, from: "src/superclaude/skills/tdd/",                        to: "skills/tdd/",                        kind: skill }
  - { source: ironclaude, from: "src/superclaude/skills/tech-reference/",             to: "skills/tech-reference/",             kind: skill }
  # - { source: ironclaude, from: "src/superclaude/skills/prd/",                       to: "skills/prd/",                        kind: skill }   # OQ-6 deferred

  # ---- Commands (7) with co-import requires — §13 + FR-4 ----
  - { source: ironclaude, from: "src/superclaude/commands/troubleshoot.md",  to: "commands/troubleshoot.md",  kind: command, requires: ["skills/sc-troubleshoot-protocol/"] }
  - { source: ironclaude, from: "src/superclaude/commands/git.md",           to: "commands/git.md",           kind: command }
  - { source: ironclaude, from: "src/superclaude/commands/cli-portify.md",   to: "commands/cli-portify.md",   kind: command, requires: ["skills/sc-cli-portify-protocol/"] }
  - { source: ironclaude, from: "src/superclaude/commands/cleanup-audit.md", to: "commands/cleanup-audit.md", kind: command }
  - { source: ironclaude, from: "src/superclaude/commands/task.md",          to: "commands/task.md",          kind: command, requires: ["skills/task/"] }
  - { source: ironclaude, from: "src/superclaude/commands/research.md",      to: "commands/research.md",      kind: command, requires: ["skills/tech-research/"] }
  - { source: ironclaude, from: "src/superclaude/commands/workflow.md",      to: "commands/workflow.md",      kind: command }

plugin:
  name: "ironops-devops"
  description: "Curated DevOps / SRE / CI-CD toolkit for Claude Code (built from IronClaude via IronOps)"
  # version intentionally omitted per FR-13

marketplace:
  name: "ironops"
  owner:
    name: "Ironbelly"
    email: "ops@example.invalid"
```

Total: 26 manifest entries — matches §10 fanout assumption (N=26 → M≈150 emitted files).

Verification needed at task-execution time: each upstream `from:` path must exist at HEAD of `IronbellyOrg/IronClaude` per §13 closing note. Co-import `requires:` fields that aren't explicit (e.g. `cleanup-audit`, `git`, `workflow`) are because those commands do not cite `Skill sc:<x>-protocol`; FR-4 enforcement is automatic when they do.

---

## 8. Build Order (Implementation Sequence)

Files with no internal dependencies first. Tests follow their target modules.

### Wave A — Project scaffolding (zero internal deps)
1. `/config/workspace/IronOps/pyproject.toml`
2. `/config/workspace/IronOps/.gitignore`
3. `/config/workspace/IronOps/.python-version`
4. `/config/workspace/IronOps/Makefile`

### Wave B — Package skeleton
5. `/config/workspace/IronOps/src/ironops/__init__.py`
6. `/config/workspace/IronOps/src/ironops/errors.py`            (FR foundation; no internal deps)

### Wave C — Core parsing/cloning (depend on errors only)
7. `/config/workspace/IronOps/src/ironops/manifest.py`           (depends: errors)
8. `/config/workspace/IronOps/src/ironops/sources.py`            (depends: errors, manifest)

### Wave D — Render and metadata (depend on manifest + sources)
9. `/config/workspace/IronOps/src/ironops/render.py`             (depends: errors, manifest, sources)
10. `/config/workspace/IronOps/src/ironops/metadata.py`          (depends: errors, manifest, sources, render)

### Wave E — Validate and publish (independent leaves used by pipeline)
11. `/config/workspace/IronOps/src/ironops/validate.py`          (depends: errors)
12. `/config/workspace/IronOps/src/ironops/publish.py`           (depends: errors, manifest, sources)

### Wave F — Orchestration
13. `/config/workspace/IronOps/src/ironops/pipeline.py`          (depends: every src/ironops/* above)
14. `/config/workspace/IronOps/src/ironops/cli.py`               (depends: pipeline, validate, errors)

### Wave G — Test scaffolding
15. `/config/workspace/IronOps/tests/__init__.py`
16. `/config/workspace/IronOps/tests/unit/__init__.py`
17. `/config/workspace/IronOps/tests/integration/__init__.py`
18. `/config/workspace/IronOps/tests/cli/__init__.py`
19. `/config/workspace/IronOps/tests/conftest.py`

### Wave H — Manifest fixtures (test inputs)
20. `/config/workspace/IronOps/tests/fixtures/ironclaude-snapshot/` (bootstrap from upstream HEAD)
21. `/config/workspace/IronOps/tests/fixtures/manifests/good.yaml`
22. `/config/workspace/IronOps/tests/fixtures/manifests/bad-schema.yaml`
23. `/config/workspace/IronOps/tests/fixtures/manifests/bad-empty-imports.yaml`
24. `/config/workspace/IronOps/tests/fixtures/manifests/bad-self-overwrite.yaml`
25. `/config/workspace/IronOps/tests/fixtures/manifests/bad-orphan-command.yaml`
26. `/config/workspace/IronOps/tests/fixtures/manifests/bad-path-escape.yaml`
27. `/config/workspace/IronOps/tests/fixtures/manifests/bad-hook-kind.yaml`

### Wave I — Unit tests (one per src/ironops/ module)
28. `/config/workspace/IronOps/tests/unit/test_errors.py`
29. `/config/workspace/IronOps/tests/unit/test_manifest.py`
30. `/config/workspace/IronOps/tests/unit/test_sources.py`
31. `/config/workspace/IronOps/tests/unit/test_render.py`
32. `/config/workspace/IronOps/tests/unit/test_metadata.py`

### Wave J — Integration tests
33. `/config/workspace/IronOps/tests/integration/test_pipeline.py`
34. `/config/workspace/IronOps/tests/integration/test_atomicity.py`
35. `/config/workspace/IronOps/tests/integration/test_negative.py`
36. `/config/workspace/IronOps/tests/fixtures/golden/ironops-devops/`  (bootstrap from first successful test_pipeline.py run)
37. `/config/workspace/IronOps/tests/integration/test_golden_output.py`

### Wave K — CLI tests
38. `/config/workspace/IronOps/tests/cli/test_cli.py`

### Wave L — Test inventory + production manifest
39. `/config/workspace/IronOps/tests/test_inventory.md`
40. `/config/workspace/IronOps/manifest.yaml`                    (the v0.1 production manifest)

### Wave M — CI workflows
41. `/config/workspace/IronOps/.github/workflows/test.yml`
42. `/config/workspace/IronOps/.github/workflows/build-publish.yml`

### Wave N — Docs and README
43. `/config/workspace/IronOps/docs/ARCHITECTURE.md`
44. `/config/workspace/IronOps/docs/MANIFEST_AUTHORING.md`
45. `/config/workspace/IronOps/docs/MARKETPLACE_BOOTSTRAP.md`
46. `/config/workspace/IronOps/docs/CHANGELOG.md`
47. `/config/workspace/IronOps/README.md` (replacement)

---

## Summary

- **Total files to create:** 47 individual files plus 2 directory-tree fixtures (`ironclaude-snapshot/`, `golden/ironops-devops/`).
- **Python source modules:** 10 (`__init__.py` + 9 functional modules in `src/ironops/`).
- **Test modules:** 11 (unit + integration + CLI + inventory).
- **Manifest fixtures:** 7 (1 good + 6 bad).
- **CI workflows:** 2 (`test.yml`, `build-publish.yml`).
- **Docs:** 4 (`ARCHITECTURE`, `MANIFEST_AUTHORING`, `MARKETPLACE_BOOTSTRAP`, `CHANGELOG`).
- **Project root:** 6 (`pyproject.toml`, `Makefile`, `.gitignore`, `.python-version`, `manifest.yaml`, `README.md`).

**FR coverage cross-check** (every FR/NFR has at least one implementing file + one test):

| Spec ID | Implementing module(s) | Test(s) |
|---|---|---|
| FR-1 | manifest.py, render.py | test_manifest, test_render, test_pipeline, test_negative |
| FR-2 | sources.py | test_sources, test_pipeline |
| FR-3 | sources.py, render.py | test_sources, test_render |
| FR-4 | render.py | test_render, test_negative |
| FR-5 | validate.py, pipeline.py | test_pipeline, test_atomicity, test_negative |
| FR-6 | metadata.py | test_metadata, test_pipeline |
| FR-7 | render.py | test_render |
| FR-8 | render.py | test_render, test_negative |
| FR-9 | pipeline.py, publish.py | test_atomicity |
| FR-10 | metadata.py | test_metadata |
| FR-11 | metadata.py | test_metadata |
| FR-12 | cli.py, pipeline.py, metadata.py | test_cli, test_pipeline, test_negative |
| FR-13 | metadata.py | test_metadata |
| FR-14 | manifest.py | test_manifest, test_negative |
| FR-15 | manifest.py | test_manifest, test_negative |
| FR-16 | manifest.py | test_manifest, test_negative |
| NFR-1 | render.py (ordering), pipeline.py | test_pipeline (determinism) |
| NFR-2 | pipeline.py (timing), sources.py (shallow clone) | test_pipeline |
| NFR-4 | validate.py | test_pipeline |
| NFR-5 | render.py (copy only, no exec) | implicit (no test needed) |
| NFR-6 | metadata.py (META.json), publish.py (commit msg) | test_metadata, test_pipeline |
| NFR-7 | errors.py, all modules | test_errors, test_negative |
| NFR-8 | manifest.py + CHANGELOG.md | test_manifest |
| NFR-9 | sources.py | test_sources |
| AC-1 | build-publish.yml | CI gating |
| AC-2 | golden fixture + test_golden_output | test_golden_output |
| AC-3 | validate.py | test_pipeline |
| AC-4 | metadata.py | test_metadata |
| AC-5 | metadata.py | test_metadata |
| AC-6 | publish.py | test_pipeline |
| AC-7 | docs/ARCHITECTURE + manual smoke | manual |
| AC-8 | tests/test_inventory.md | inventory matrix |
| AC-9 | full guard-row coverage across tests | test_manifest + test_render |
| AC-10 | test_negative.py | test_negative |

**Status:** Complete
