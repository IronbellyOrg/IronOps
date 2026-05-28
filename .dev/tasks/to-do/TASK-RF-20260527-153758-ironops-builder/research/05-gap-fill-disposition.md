# Research 05 — Gap-Fill: Disposition of rf-qa Findings

**Status:** Complete
**Author:** orchestrator (task-builder skill)
**Date:** 2026-05-27
**Cycle:** 1 (first gap-fill)
**Resolves:** rf-qa research-gate report findings at `qa/qa-research-gate-report.md` (1 CRITICAL + 4 IMPORTANT + 3 MINOR)
**Purpose:** Document the orchestrator's binding disposition for every finding so the rf-task-builder receives one unambiguous instruction per concern.

This file is **authoritative** — it overrides any earlier contradiction in the four researcher files. Where prior researcher output contradicts a disposition below, the disposition below wins. The rf-task-builder MUST treat this file as the tiebreaker.

---

## Disposition 1 — CRITICAL-1: Manifest format is YAML (not JSON)

**rf-qa finding:** Researcher 02 §2.2 line 117 and "Explicit non-copies" line 933 suggest dropping `pyyaml` and using JSON for the v0.1 manifest. This contradicts the spec, the research notes, and researchers 01/04.

**Disposition: YAML wins. No JSON manifest in v0.1.**

**Evidence supporting YAML:**
- **SPEC §5** (Manifest Schema Requirements): explicitly defines the manifest as YAML, with concrete `manifest.yaml` example.
- **SPEC §16 OQ-1**: "YAML recommended (matches IronClaude convention). Confirm during task-builder phase before locking schema." — confirmed and locked here.
- **research-notes.md** GAPS_AND_QUESTIONS Q-Resolved: "Manifest YAML library → PyYAML (standard, in IronClaude's deps tree)."
- **research/01-file-inventory.md**: `manifest.yaml` is the canonical name throughout the file inventory.
- **research/04-test-and-integration-patterns.md**: fixture set includes `tests/fixtures/manifests/*.yaml`.

**Researcher 02's contrary hint:** the "drop pyyaml" recommendation in researcher 02 reflects researcher 02's local preference for minimal dependencies. It is overridden. PyYAML is added to runtime dependencies in `pyproject.toml`.

**Builder instruction:** Implement `src/ironops/manifest.py` using `yaml.safe_load`. Add `pyyaml>=6.0` to `[project.dependencies]` in `pyproject.toml`. All test fixtures are `*.yaml`. No JSON manifest support, even as a future option.

---

## Disposition 2 — IMPORTANT-1: CLI is a flat `src/ironops/cli.py` module (not a subpackage)

**rf-qa finding:** Researcher 02 §1.2 hints at `src/ironops/cli/main.py` (subpackage). Researcher 01 §1.10 prescribes flat `src/ironops/cli.py` module.

**Disposition: Flat `src/ironops/cli.py` module wins.**

**Rationale:** IronOps' v0.1 CLI has exactly two subcommands (`build` and `validate`) plus optional flags. A subpackage layout is overhead with no benefit. The flat module is consistent with researcher 01's file inventory and easier to grok for a single-file CLI.

**Builder instruction:** `src/ironops/cli.py` is a single Python module exposing one `click.group()` named `cli` and two subcommands. Entry point in `pyproject.toml` is `ironops = "ironops.cli:cli"`.

---

## Disposition 3 — IMPORTANT-2: `PUBLISH_FAILED` is an explicit spec amendment (not a silent extension)

**rf-qa finding:** Researcher 04 §B.7 flagged that rsync/git-push failures don't map to any spec NFR-7 code. Researcher 01 §1.2 silently added `PUBLISH_FAILED=18` to the `ExitCode` enum. rf-qa correctly notes this should be an explicit spec amendment, not a hidden extension.

**Disposition: Add `PUBLISH_FAILED` as an explicit, documented amendment to SPEC §NFR-7.**

The task file will include a dedicated checklist item to **amend the spec** by appending `PUBLISH_FAILED` to the categorical failure code list in NFR-7. This is a deliberate, documented spec evolution — not an inferred extension.

**Updated NFR-7 categorical code list (post-amendment, 9 codes total):**
1. `MANIFEST_INVALID`
2. `UNRESOLVED_IMPORT`
3. `CO_IMPORT_MISSING`
4. `VALIDATE_FAILED`
5. `PATH_ESCAPE`
6. `UPSTREAM_CLONE_FAILED`
7. `SELF_OVERWRITE`
8. `BUILDER_DIRTY_TREE`
9. **`PUBLISH_FAILED`** ← new in v0.1 implementation; spec amendment captured in task

**Builder instruction:** The task file MUST include (in Phase 1 or Phase 7) a checklist item that edits `/config/workspace/IronOps/.dev/releases/1.0/0.1/SPEC_IRONOPS_DEVOPS_PLUGIN.md` §NFR-7 to add `PUBLISH_FAILED` to the categorical code list. The implementation in `src/ironops/errors.py` then aligns with the amended spec, not silently extends it.

---

## Disposition 4 — IMPORTANT-3: Builder lives in `src/ironops/` package (deliberate enhancement of SPEC §2.1)

**rf-qa finding:** SPEC §2.1 says the builder is `scripts/build_plugin.py` + helpers. Researcher 01 prescribes a `src/ironops/` package layout. Deviation should be flagged explicitly.

**Disposition: `src/ironops/` package wins. SPEC §2.1 is amended via task to reflect the package layout.**

**Rationale:** A `src/ironops/` package with `cli.py` providing a `ironops` entry point is:
- Installable via `uv pip install -e .` (matches IronClaude convention)
- Testable as a real Python package (imports, modules, fixtures)
- Versioned via `pyproject.toml`
- Distributable via `pipx install ironops` if we ever want that
- Consistent with how the project is described in researcher 02's IronClaude reference patterns

`scripts/build_plugin.py` as a flat script is acceptable for a one-off tool, but unsuitable for a CI-driven, tested, evolved builder.

**Builder instruction:** Implementation lives in `src/ironops/{cli,manifest,sources,render,metadata,validate,publish,pipeline,errors}.py`. The task includes a docs item that amends SPEC §2.1 to clarify that the builder is the `ironops` CLI package (`src/ironops/`), with `scripts/` reserved only for future helper scripts.

---

## Disposition 5 — IMPORTANT-4: `--allow-dirty` flag is dropped (no spec basis)

**rf-qa finding:** Researcher 04 §B.5 invented a `--allow-dirty` CLI flag to override FR-12's dirty-tree guard. No spec authorization.

**Disposition: `--allow-dirty` is DROPPED.** FR-12 is HARD-fail. A dirty working tree on the IronOps repo aborts the build with `BUILDER_DIRTY_TREE`, period.

**Rationale:** FR-12 makes the build deterministic. Allowing override defeats the determinism property. If a developer needs to test mid-edit, they commit a WIP commit (`git commit -m "WIP" --no-verify` — separate concern).

**Builder instruction:** `src/ironops/cli.py` has NO `--allow-dirty` flag. `src/ironops/pipeline.py` Stage 0 (PREFLIGHT) checks `git -C <ironops-repo> status --porcelain` and aborts unconditionally with `BUILDER_DIRTY_TREE` if non-empty.

---

## Disposition 6 — MINOR-1: Researcher 02 status header is a cosmetic typo

**rf-qa finding:** `research/02-ironclaude-reference-patterns.md` Status header says "In Progress" while body ends with "Complete".

**Disposition: Documented; cosmetic only.** Task does NOT need an item to fix this — the file is read by the rf-task-builder for its CONTENT, and the content is sound. The task file's research-related items reference the file by path, not by status header.

---

## Disposition 7 — MINOR-2: `[CODE-VERIFIED]` tags are partially absent from researcher files

**rf-qa finding:** Documentation Staleness Protocol tags (`[CODE-VERIFIED]`/`[CODE-CONTRADICTED]`/`[UNVERIFIED]`) are missing from most research files.

**Disposition: Acceptable for this run.**

**Rationale:** The Doc Staleness Protocol applies when researchers cite EXISTING ARCHITECTURE from documentation. In a greenfield project:
- Researcher 01 (file inventory) describes files TO BE CREATED, not existing architecture. There is nothing to verify against code yet.
- Researcher 02 (IronClaude reference patterns) cites `file:line` for every pattern — `file:line` IS the verification.
- Researcher 03 (MDTM template) cites template section IDs — the template file existence and section IDs are already verified.
- Researcher 04 (test patterns + integration) cites `file:line` for IronClaude patterns and spec FR IDs for integration shapes — both are verified.

The one [CODE-CONTRADICTED] finding (IronClaude's `build_superclaude_plugin.py` is broken) IS tagged and verified by rf-qa (spot-checked at `scripts/build_superclaude_plugin.py:15-22`).

**Builder instruction:** No action needed; the protocol applies for documentation-based claims and the research base is `file:line`-cited for greenfield design.

---

## Disposition 8 — MINOR-3: NFR-3 (context cost budget) is missing from researcher 01's FR/NFR coverage table

**rf-qa finding:** Researcher 01's FR/NFR coverage table omits NFR-3 (per-session token cost budget).

**Disposition: Acknowledge; encode in the task as a docs item.**

NFR-3 is enforced at PRESENTATION time (after install, via `claude plugin details ironops-devops`), not at BUILD time. The builder does not need a module to enforce it. The task file MUST include a docs item in `docs/MANIFEST_AUTHORING.md` stating "NFR-3: keep total context cost below 1500 tokens always-on. Use `claude plugin details ironops-devops` post-install to verify."

**Builder instruction:** Add an entry to `docs/MANIFEST_AUTHORING.md` covering NFR-3 enforcement strategy. No source-code module needed.

---

## Disposition 9 — Researcher 02's "drop scheduled workflow trigger" and other minor non-copies

**Not flagged by rf-qa but worth pinning:** Researcher 02 lists several "explicit non-copies" — patterns from IronClaude IronOps should NOT inherit (anthropic SDK ban, force-include hatchling hack, argparse, pexpect, jsonschema, ContentTransformer, etc.).

**Disposition: All "non-copies" are accepted.** Researcher 02's adaptation guidance is correct. Builder instruction is: do not adopt the listed anti-patterns.

The one exception: the scheduled-workflow trigger. SPEC §UC-1 says builds are triggered by push to `main`, scheduled rebuild, or manual `workflow_dispatch`. So the scheduled trigger IS in scope (just less critical for v0.1 — a daily cron suffices). The task includes a `schedule:` block in `.github/workflows/build-publish.yml`.

---

## Summary of Authoritative Decisions (one-line each)

| # | Topic | Disposition |
|---|---|---|
| D1 | Manifest format | **YAML** (PyYAML runtime dep). No JSON. |
| D2 | CLI layout | **Flat `src/ironops/cli.py`** module (single click group, 2 subcommands). |
| D3 | NFR-7 codes | **9 codes** total. `PUBLISH_FAILED` added as explicit spec amendment. |
| D4 | Builder location | **`src/ironops/` package** (not `scripts/`). Spec §2.1 amended via task. |
| D5 | Dirty-tree flag | **Dropped.** FR-12 is HARD-fail. No `--allow-dirty`. |
| D6 | Researcher 02 status header | Cosmetic typo; no fix needed. |
| D7 | `[CODE-VERIFIED]` tags | Acceptable absence in greenfield; `file:line` is the verification. |
| D8 | NFR-3 enforcement | Docs item in `MANIFEST_AUTHORING.md`; no source module. |
| D9 | Researcher 02 "non-copies" | All accepted. Scheduled-workflow trigger DOES apply (in scope). |

---

## Spec Amendments Captured for the Task

The task file will include two **explicit spec-amendment items** (after the spec read; before implementation phases lock in):

1. **Amend SPEC §NFR-7**: append `PUBLISH_FAILED` to the categorical failure code list.
2. **Amend SPEC §2.1**: clarify that the builder is the `ironops` CLI package at `src/ironops/`, with `scripts/` reserved for future helper scripts.

Both amendments are concrete `Edit` operations on the existing spec file. They are NOT inferred or implied — they are documented changes the executor performs.

---

## Status

All 8 rf-qa findings dispositioned. The rf-task-builder is instructed to:
- Treat this file as the tiebreaker over any earlier researcher contradiction.
- Include the two spec-amendment items as explicit checklist items.
- Build everything else per the existing researcher files, with the authoritative decisions above applied.
