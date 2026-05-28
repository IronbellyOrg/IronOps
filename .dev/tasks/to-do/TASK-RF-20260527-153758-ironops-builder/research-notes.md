# Research Notes: Implement IronOps DevOps Claude Plugin v0.1 Builder

**Date:** 2026-05-27
**Scenario:** A (explicit — full implementation-ready spec provided)
**Depth Tier:** Standard (well-specced; 4 researchers, no web)
**Track Count:** 1 (single cohesive output — the IronOps builder + tests + CI workflow + initial manifest)
**Status:** Complete

---

## EXISTING_FILES

### Target repo: IronOps (greenfield)

Verified via `ls -la /config/workspace/IronOps/`:

| Path | Purpose |
|---|---|
| `/config/workspace/IronOps/LICENSE` | Existing license file (preserve) |
| `/config/workspace/IronOps/README.md` | Stub (36 bytes); replace at end |
| `/config/workspace/IronOps/.dev/releases/1.0/0.1/SPEC_IRONOPS_DEVOPS_PLUGIN.md` | **Authoritative spec** (~500 lines); FR-1..FR-16, NFR-1..NFR-9 |
| `/config/workspace/IronOps/.dev/tasks/to-do/TASK-RESEARCH-20260527-150111-ironops-plugin-aggregator/` | Decision brief + 3 research files from spec-phase |
| `/config/workspace/IronOps/.dev/tasks/to-do/TASK-RF-20260527-153758-ironops-builder/` | **This task's workspace** |

Everything else under IronOps needs to be CREATED by the task. No `pyproject.toml`, no `Makefile`, no `src/`, no `tests/`, no `.github/`, no `scripts/`, no `manifest.yaml`.

### Reference (IronClaude — read-only inspiration; NOT to copy)

Verified via `ls` and `Read` in this session:

| Path | Reference value |
|---|---|
| `/config/workspace/IronClaude/scripts/build_superclaude_plugin.py` | 101-line builder reading a manifest dir and rendering a plugin tree. **Partially broken — references `plugins/superclaude/manifest/` that doesn't exist.** Useful as: structural pattern (render_template, copy_tree, manifest separation) |
| `/config/workspace/IronClaude/scripts/sync_from_framework.py` | 700+ line full-repo sync script with content transforms. Useful as: GitHub Actions integration, file-syncing patterns, `--dry-run` flag conventions. NOT a copy target — IronOps uses manifest allowlist, not whole-repo sync |
| `/config/workspace/IronClaude/.github/workflows/test.yml` | Standard test workflow: UV install, pytest matrix on Python 3.10/3.11/3.12, coverage to Codecov |
| `/config/workspace/IronClaude/.github/workflows/pull-sync-framework.yml` | Scheduled+manual sync workflow with `git ls-remote` HEAD check, last-sync-commit file, protection-file verification. Useful pattern for IronOps build-publish workflow |
| `/config/workspace/IronClaude/Makefile:65-87` | `build-plugin` and `sync-plugin-repo` target structure |
| `/config/workspace/IronClaude/tests/cli/test_cli_registration.py` | pytest test layout pattern |
| `/config/workspace/IronClaude/src/superclaude/templates/workflow/02_mdtm_template_complex_task.md` | **MDTM Template 02 — source of truth path** (`.claude/templates/workflow/02_*` does NOT exist; `.claude/templates/workflow/` only has 03/04/05/06) |
| `/config/workspace/IronClaude/src/superclaude/templates/workflow/01_mdtm_template_generic_task.md` | MDTM Template 01 |
| `/config/workspace/IronClaude/.dev/tasks/to-do/TASK-RF-20260525-194356/TASK-RF-20260525-194356.md` | **Concrete reference task file** following Template 02 — frontmatter shape, phase structure, B2 self-contained items, related_docs pattern |

### Important file-location finding [CODE-VERIFIED]

The MDTM templates `02_mdtm_template_complex_task.md` and `01_mdtm_template_generic_task.md` are **only at `src/superclaude/templates/workflow/`**, not at `.claude/templates/workflow/`. The `.claude/templates/workflow/` directory contains 03/04/05/06 only. **The rf-task-builder BUILD_REQUEST must use the `src/superclaude/templates/workflow/` path.** This contradicts the default skill text and is captured here so the builder can resolve correctly.

---

## PATTERNS_AND_CONVENTIONS

### Python project conventions (IronClaude reference)

- **UV is mandatory** — `uv pip install --system -e ".[dev]"`, `uv run pytest`. Never `python -m pip`.
- **Build system:** hatchling (PEP 517), `pyproject.toml`.
- **Test runner:** pytest, organized under `tests/{unit,integration,cli}/`.
- **Lint/format:** ruff (`make lint`, `make format`).
- **Dependency table:** `pyproject.toml` `[project.dependencies]` and `[project.optional-dependencies].dev`.

### CI/CD conventions

- **Workflow files:** `.github/workflows/<name>.yml`.
- **UV install pattern:** `curl -LsSf https://astral.sh/uv/install.sh | sh; echo "$HOME/.cargo/bin" >> $GITHUB_PATH`.
- **Matrix testing:** Python 3.10–3.12.
- **Trigger patterns:** `push`+`pull_request` for tests; `schedule` cron + `workflow_dispatch` for syncs.
- **Authentication:** `GITHUB_TOKEN` for repo access; deploy keys for SSH; `permissions: contents: write` for pushing.
- **Protection checks:** verify-no-modification of named files post-run (`git diff --name-only HEAD -- <path>`).

### Reference builder patterns (do NOT copy verbatim — adapt)

From `scripts/build_superclaude_plugin.py`:
- Module-level `ROOT = Path(__file__).resolve().parents[1]` for repo root.
- Function decomposition: `load_metadata()`, `render_template()`, `copy_tree()`, `main()`.
- `shutil.rmtree(DIST_ROOT) + DIST_ROOT.mkdir(parents=True, exist_ok=True)` for clean staging.
- `shutil.copytree(src, dest, dirs_exist_ok=True)` for directory imports.
- Template rendering: simple `{{key}}` string substitution.

From `scripts/sync_from_framework.py`:
- `@dataclass class SyncResult` for typed results.
- `class ContentTransformer:` + `class FileSyncer:` + orchestrator `class FrameworkSync:`.
- `subprocess.run(["git", "rev-parse", "--git-dir"], ...)` for git availability check.
- `logger = logging.getLogger(__name__)` per-module.
- `--dry-run` flag everywhere; `argparse` with subcommands.

### Spec-imposed conventions (from SPEC §3-§7)

- **`schema_version: "1"` required** on manifest (FR-14).
- **Categorical failure codes** (NFR-7): `MANIFEST_INVALID`, `UNRESOLVED_IMPORT`, `CO_IMPORT_MISSING`, `VALIDATE_FAILED`, `PATH_ESCAPE`, `UPSTREAM_CLONE_FAILED`, `SELF_OVERWRITE`, `BUILDER_DIRTY_TREE`. Builder must emit one of these on every non-zero exit.
- **Atomic publish via staging dir** (FR-9) — render to staging, validate there, then `rsync --delete` to marketplace repo. Never write directly to the publish target.
- **`${CLAUDE_PLUGIN_ROOT}` placeholder** — recognized but not interpolated by the builder; passed through to Claude Code runtime.
- **No file content rewriting** for agents/skills (FR-7-A2) — byte-identical to upstream.
- **omit `plugin.json.version`** in v0.1 (FR-13).
- **Reproducibility** (NFR-1) — `META.json.built_at` is the only permitted non-determinism source.

---

## GAPS_AND_QUESTIONS

Open questions explicitly carried over from SPEC §16 — these become task items that document decisions rather than blockers:

1. **OQ-1 Manifest format:** YAML vs TOML. Spec recommends YAML; task locks YAML in implementation phase.
2. **OQ-2 Skill directory rename:** keep `sc-troubleshoot-protocol` as-is for v0.1 per spec FR-7.
3. **OQ-3 Marketplace repo bootstrap:** `IronbellyOrg/ironops-marketplace` may not exist yet — builder's first successful build pushes initial commit. Task includes a docs item describing manual bootstrap (`git init --bare` on the GitHub side) but does NOT implement repo creation.
4. **OQ-4 Auth model:** `GITHUB_TOKEN` secret in CI for both upstream clones and marketplace push. PAT with `repo` scope.
5. **OQ-5 Test fixtures:** snapshot a known-good IronClaude commit into `tests/fixtures/ironclaude-snapshot/` (small subset — just the manifest's selected files at one commit). Task includes a fixture-bootstrap item.
6. **OQ-6 `prd` skill inclusion:** spec defers to v0.1 manifest authoring phase. Task: manifest entry exists but is **commented out** with a note for later.
7. **OQ-7 License audit cadence:** automated per-build attribution is in scope (FR-11); a separate human cadence is out of scope for this task.
8. **OQ-8 Builder output verbosity:** simple — INFO to stdout, DEBUG only with `--verbose`.
9. **OQ-9 Other components (`monitors/`, `.lsp.json`, `bin/`, `output-styles/`, `themes/`):** all out of scope; manifest schema reserves `kind` values for future use.
10. **OQ-10 Onboarding command:** out of scope for v0.1.

These appear as **Open Questions** in the task file's Task Log section, NOT as the basis for implementation items.

### Resolved during scope discovery (was unclear in spec)

- **Q-Resolved:** MDTM Template 02 actual path → `src/superclaude/templates/workflow/02_mdtm_template_complex_task.md` (verified — `.claude/templates/workflow/02_*` does not exist).
- **Q-Resolved:** Builder language → Python 3.11+ (matches IronClaude). pyproject.toml + UV.
- **Q-Resolved:** Test layout → mirror IronClaude: `tests/{unit,integration,cli}/` + `tests/fixtures/`.
- **Q-Resolved:** Manifest YAML library → `PyYAML` (standard, in IronClaude's deps tree).
- **Q-Resolved:** Marketplace push mechanic → `subprocess.run(["git", "add", ...])` + commit + push from within the marketplace-repo clone.

---

## RECOMMENDED_OUTPUTS

The task file (when executed) will produce:

| File/Directory | Purpose | Spec ref |
|---|---|---|
| `/config/workspace/IronOps/pyproject.toml` | Package metadata, dependencies, ruff config | NFR-1, conventions |
| `/config/workspace/IronOps/Makefile` | `dev`, `lint`, `format`, `test`, `build` targets | conventions |
| `/config/workspace/IronOps/.gitignore` | Standard Python ignores + `dist/`, `.venv/`, `__pycache__/` | hygiene |
| `/config/workspace/IronOps/manifest.yaml` | The v0.1 manifest, schema_version "1", v0.1 component shortlist | §5, §13 |
| `/config/workspace/IronOps/src/ironops/__init__.py` | Package init with version | structure |
| `/config/workspace/IronOps/src/ironops/cli.py` | Click CLI entry point (`ironops build`, `ironops validate`) | FR-12 |
| `/config/workspace/IronOps/src/ironops/manifest.py` | Manifest parser + schema validation | FR-1, FR-14, FR-15, FR-16 |
| `/config/workspace/IronOps/src/ironops/sources.py` | Upstream clone + default-branch resolution | FR-2, FR-3 |
| `/config/workspace/IronOps/src/ironops/render.py` | Copy from upstream-clone → staging-dir, co-import enforcement, path-safety | FR-4, FR-7, FR-8 |
| `/config/workspace/IronOps/src/ironops/metadata.py` | Emit `plugin.json`, `META.json`, `THIRD_PARTY_LICENSES.md`, `marketplace.json` | FR-6, FR-10, FR-11, FR-13, §6 |
| `/config/workspace/IronOps/src/ironops/validate.py` | Invoke `claude plugin validate` subprocess | FR-5 |
| `/config/workspace/IronOps/src/ironops/publish.py` | rsync to marketplace-repo clone + commit + push | FR-9 |
| `/config/workspace/IronOps/src/ironops/pipeline.py` | Orchestrator wiring the 8 stages with atomicity | §7 |
| `/config/workspace/IronOps/src/ironops/errors.py` | Categorical exit-code enum (NFR-7 codes) | NFR-7 |
| `/config/workspace/IronOps/tests/conftest.py` | pytest fixtures | |
| `/config/workspace/IronOps/tests/fixtures/manifests/good.yaml` | Valid manifest fixture | tests |
| `/config/workspace/IronOps/tests/fixtures/manifests/bad-schema.yaml` | schema_version mismatch | FR-14 neg |
| `/config/workspace/IronOps/tests/fixtures/manifests/bad-empty-imports.yaml` | empty imports list | FR-15 neg |
| `/config/workspace/IronOps/tests/fixtures/manifests/bad-self-overwrite.yaml` | targets `META.json` | FR-16 neg |
| `/config/workspace/IronOps/tests/fixtures/manifests/bad-orphan-command.yaml` | command without companion skill | FR-4 neg |
| `/config/workspace/IronOps/tests/fixtures/manifests/bad-path-escape.yaml` | `to: "../../etc"` | FR-8 neg |
| `/config/workspace/IronOps/tests/fixtures/ironclaude-snapshot/` | small fixture mimicking IronClaude tree | hermetic tests |
| `/config/workspace/IronOps/tests/unit/test_manifest.py` | Manifest parser tests | FR-1, FR-14, FR-15, FR-16 |
| `/config/workspace/IronOps/tests/unit/test_sources.py` | Source resolution + default-branch | FR-2 |
| `/config/workspace/IronOps/tests/unit/test_render.py` | Co-import enforcement + path safety | FR-4, FR-7, FR-8 |
| `/config/workspace/IronOps/tests/unit/test_metadata.py` | META.json schema, plugin.json shape | FR-6, FR-13, §6 |
| `/config/workspace/IronOps/tests/unit/test_errors.py` | Categorical exit codes | NFR-7 |
| `/config/workspace/IronOps/tests/integration/test_pipeline.py` | End-to-end pipeline against fixture | All FRs |
| `/config/workspace/IronOps/tests/integration/test_atomicity.py` | Mid-pipeline failure leaves marketplace unchanged | FR-9 |
| `/config/workspace/IronOps/tests/integration/test_negative.py` | All malformed-manifest fixtures fail correctly | AC-10 |
| `/config/workspace/IronOps/tests/integration/test_golden_output.py` | Snapshot diff against committed golden plugin tree | AC-2 |
| `/config/workspace/IronOps/tests/integration/test_smoke.py` | install-and-invoke smoke test (optional, may need claude binary) | AC-7 |
| `/config/workspace/IronOps/.github/workflows/build-publish.yml` | Build + validate + push on `main` + dispatch | UC-1, AC-1 |
| `/config/workspace/IronOps/.github/workflows/test.yml` | Run tests on push/PR | conventions |
| `/config/workspace/IronOps/docs/ARCHITECTURE.md` | Brief architecture overview pointing at the spec | docs |
| `/config/workspace/IronOps/docs/MANIFEST_AUTHORING.md` | How to add/remove imports from manifest.yaml | docs |
| `/config/workspace/IronOps/docs/MARKETPLACE_BOOTSTRAP.md` | How to set up `IronbellyOrg/ironops-marketplace` initially | OQ-3 |
| `/config/workspace/IronOps/README.md` | Replace stub with builder usage + install instructions | |

**Total estimated files: ~40-45.**

---

## SUGGESTED_PHASES

Researcher assignments (4 researchers, parallel via Agent tool):

### Researcher 1 — File Inventory & Greenfield Structure

- **Topic type:** File Inventory (adapted for greenfield)
- **Scope:** Enumerate every file IronOps needs based on SPEC §5 (manifest schema), §6 (META.json schema), §7 (pipeline stages), §12 (acceptance criteria), §13 (component shortlist), §14 (test strategy).
- **Output:** `/config/workspace/IronOps/.dev/tasks/to-do/TASK-RF-20260527-153758-ironops-builder/research/01-file-inventory.md`
- **Specifics:** For each output file in RECOMMENDED_OUTPUTS above, document: full path, purpose, key functions/classes/structures expected, line-count estimate, which FRs it implements, dependencies on other files.
- **Other researchers covering:** patterns (R2), templates (R3), test/CI patterns (R4) — do NOT duplicate their work.

### Researcher 2 — Patterns from IronClaude (reference; not copying)

- **Topic type:** Patterns & Conventions
- **Scope:** Read `/config/workspace/IronClaude/scripts/build_superclaude_plugin.py`, `/config/workspace/IronClaude/scripts/sync_from_framework.py`, `/config/workspace/IronClaude/Makefile` (relevant targets), `/config/workspace/IronClaude/pyproject.toml`, and `/config/workspace/IronClaude/.github/workflows/{test.yml,pull-sync-framework.yml,quick-check.yml}`.
- **Output:** `/config/workspace/IronOps/.dev/tasks/to-do/TASK-RF-20260527-153758-ironops-builder/research/02-ironclaude-reference-patterns.md`
- **Specifics:** Extract Python project layout, UV+pytest convention, click CLI pattern, dataclass result types, subprocess+git interaction patterns, GitHub Actions workflow shape (matrix, install, env, permissions), `--dry-run` flag pattern, scheduled+manual trigger pattern. Cite file:line for every pattern. **CRITICAL:** mark each pattern as "adapt for IronOps" — these are NOT copy targets; IronOps must own its code.
- **Other researchers covering:** file inventory (R1), templates (R3), test patterns (R4) — focus only on extracting patterns to follow.

### Researcher 3 — MDTM Template 02 + Reference Task Example

- **Topic type:** Template & Examples
- **Scope:** Read `/config/workspace/IronClaude/src/superclaude/templates/workflow/02_mdtm_template_complex_task.md` in full (PART 1 + PART 2). Also read the reference task at `/config/workspace/IronClaude/.dev/tasks/to-do/TASK-RF-20260525-194356/TASK-RF-20260525-194356.md` for a working Template-02 example.
- **Output:** `/config/workspace/IronOps/.dev/tasks/to-do/TASK-RF-20260527-153758-ironops-builder/research/03-mdtm-template-and-examples.md`
- **Specifics:** Document required template sections (A1-A6, B1-B7, C1-C4, D1-D3, E1-E2, F1-F4, G1-G3, H1-H3, I1-I17, J1-J3, K1-K4, L1-L4), the B2 self-contained pattern with concrete example, the A3 granularity rule, the I-section phase-gate handling, mandatory anti-orphaning (task completion items inside final phase). From the reference task, note: frontmatter shape, phase header style, embedded validation commands, related_docs structure.
- **Other researchers covering:** file inventory (R1), patterns (R2), tests (R4) — focus exclusively on MDTM rules and what the generated task file must look like.

### Researcher 4 — Integration Points & Test Patterns

- **Topic type:** Integration Points + Test & Verification (combined)
- **Scope:** Read `/config/workspace/IronClaude/tests/conftest.py`, `/config/workspace/IronClaude/tests/cli/test_cli_registration.py`, 2-3 other representative test files. Also examine how `claude plugin validate` is invoked (spec FR-5) and what the marketplace repo push mechanic needs.
- **Output:** `/config/workspace/IronOps/.dev/tasks/to-do/TASK-RF-20260527-153758-ironops-builder/research/04-test-and-integration-patterns.md`
- **Specifics:** pytest fixture patterns (conftest, parametrization, tmp_path), CLI testing via `click.testing.CliRunner`, subprocess mocking (`monkeypatch.setattr` vs `subprocess.run` real call), assertion idioms. Then map IronOps integration points: (a) git CLI invocations for clone, (b) `claude plugin validate` subprocess invocation, (c) rsync invocation, (d) marketplace-repo git push. For each, document expected command shape and failure handling.
- **Other researchers covering:** file inventory (R1), patterns (R2), templates (R3) — focus on test/integration concrete details.

---

## TEMPLATE_NOTES

- **Template selection:** Template 02 (complex). Justification: multi-phase (scaffold → core modules → tests → CI → docs → integration), parallel-friendly within phases (e.g., independent unit-test items), conditional flow (tests that need fixtures vs tests that don't), and validation gates (lint/test must pass before integration).
- **Tier selection:** Standard. Justification: 40-45 new files, well-specced; single-track because all outputs converge into one cohesive builder; no web research needed (spec contains all external references).
- **Granularity (A3/A4):** every file gets its own checklist item. Tests get one item per test module. Workflow YAML is one item. README/docs are individual items.
- **Phase structure recommended:**
  - **Phase 1 — Project Scaffolding:** pyproject.toml, Makefile, .gitignore, .python-version, src/ironops/__init__.py
  - **Phase 2 — Core Module Implementation:** errors.py, manifest.py, sources.py, render.py, metadata.py, validate.py, publish.py, pipeline.py, cli.py (one item each; in dependency order)
  - **Phase 3 — Test Fixtures:** good/bad manifest YAML fixtures, ironclaude-snapshot fixture bootstrap
  - **Phase 4 — Unit Tests:** test_manifest, test_sources, test_render, test_metadata, test_errors (one item each)
  - **Phase 5 — Integration Tests:** test_pipeline, test_atomicity, test_negative, test_golden_output (one item each)
  - **Phase 6 — CI Workflows:** build-publish.yml, test.yml (one item each)
  - **Phase 7 — Initial Manifest & Docs:** manifest.yaml with v0.1 shortlist, ARCHITECTURE.md, MANIFEST_AUTHORING.md, MARKETPLACE_BOOTSTRAP.md, README.md
  - **Phase 8 — Validation:** `uv run pytest`, `make lint`, `make build` smoke run, frontmatter close-out
- **QA gates inside generated task file:** Per Critical Rule #16 — since BUILD_REQUEST will specify `QA_GATE_REQUIREMENTS: PER_PHASE` and `TESTING_REQUIREMENTS: UNIT + INTEGRATION` and `VALIDATION_REQUIREMENTS` (lint + test + build), the generated task file must include validation/QA items between phases (especially between implementation and tests, and between tests and CI).
- **Estimated total items:** 40-50 across 8 phases.

---

## AMBIGUITIES_FOR_USER

None blocking task-file generation. Operational ambiguities that the executor will hit at execution time and resolve in-flight:

- `IronbellyOrg/ironops-marketplace` repo may not exist at first build → docs item explains manual bootstrap (gh repo create) and the builder accepts a fresh empty repo.
- `claude` CLI may not be installed in the IronOps CI runner → CI workflow installs it; the smoke test for AC-7 is gated on `claude --version` succeeding.
- `tests/fixtures/ironclaude-snapshot/` requires a real snapshot — the task includes a "bootstrap from upstream HEAD at commit X" item that pins X to whatever IronClaude HEAD is on the day the task is executed.

All ten Open Questions from SPEC §16 are captured above as documented decisions, not blockers.
