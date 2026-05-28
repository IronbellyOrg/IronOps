# QA Report — Research Gate

**Topic:** IronOps DevOps Claude Plugin builder v0.1
**Date:** 2026-05-27
**Phase:** research-gate
**Fix cycle:** 1 (initial pass)
**Fix authorization:** false (report-only)
**Adversarial stance:** ACTIVE — assume errors present until proven otherwise.

---

## Scope

Assigned files (4 of 4 — single-instance, full scope):

- 01-file-inventory.md
- 02-ironclaude-reference-patterns.md
- 03-mdtm-template-and-examples.md
- 04-test-and-integration-patterns.md

Cross-reference inputs: spec at `/config/workspace/IronOps/.dev/releases/1.0/0.1/SPEC_IRONOPS_DEVOPS_PLUGIN.md`, research-notes (if present), IronClaude source tree.

Verification log appended incrementally below.

---

## Overall Verdict: FAIL

The four research files are individually rigorous, well-cited, and largely correct in their evidence base. However the cohort contains one CRITICAL inter-researcher contradiction (manifest format / pyyaml dep), one IMPORTANT inter-researcher disagreement on CLI package layout, three IMPORTANT spec-drift items (spec gap reframed as recommendation rather than surfaced; spec's `scripts/build_plugin.py` location ignored without flagging; `--allow-dirty` flag invented without spec basis), and several MINOR gaps in evidence-tagging discipline. Per the gate rule, ALL findings of any severity = FAIL. None of these are unfixable; they are documentation/reconciliation issues, not research-quality issues.

---

## Items Reviewed

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | File inventory — Status: Complete + Summary on every research file | PASS | File 01 line 5 (`Status: Complete`), Summary section at line 1157. File 02 lines 3 + 937 (`Status: In Progress` at top, `Status: Complete` at bottom — minor inconsistency, noted MINOR). File 03 line 3 (`Status: Complete`), Summary line 396. File 04 line 3 (`Status: Complete`), Summary line 657. research-notes.md line 7 (`Status: Complete`). |
| 2 | Evidence density — file paths and line ranges cited | PASS | Spot-checked: file 02 cites pyproject.toml:72-77 (verified), :64-66 (verified), :34-56 (verified); cli/main.py:18-26 (verified), :215-258 (verified); scripts/sync_from_framework.py:47-65 (verified), :158-172 (verified). File 03 cites Template 02 + reference task — both exist. File 04 cites conftest.py:13-15, :28-79, :82-117 (verified). File 01 spot-checked: all 11 agent paths + 8 skill dirs + 7 command paths in §13 shortlist verified to exist in IronClaude tree. Density rated DENSE (>80% evidenced) across all four files. |
| 3 | Scope coverage — every spec FR/NFR/AC has an implementing module + verification | PASS | File 01 §1.1–§8 enumerates 47 files across Waves A–N. The FR/NFR/AC traceability table at lines 1167–1204 maps every FR-1..FR-16, NFR-1..NFR-9, AC-1..AC-10 to an implementing module AND a test. Spot-checked: NFR-3 (token cost budget) is the only spec line not in the table — minor gap (see MINOR-3). All 8 pipeline stages from spec §7 have a file (`pipeline.py`) and a test. |
| 4 | Documentation cross-validation — [CODE-VERIFIED]/[CODE-CONTRADICTED]/[UNVERIFIED] tags on doc claims | PARTIAL FAIL | Only research-notes.md uses the tag pattern (one [CODE-VERIFIED] tag at line 43). The four research files contain doc-derived claims (e.g., file 02's `build_superclaude_plugin.py is partially broken` claim at line 10) without explicit tags. Spot-verified the broken-script claim against scripts/build_superclaude_plugin.py:15-22 — `MANIFEST_DIR = PLUGIN_SRC / "manifest"` reads from `plugins/superclaude/manifest/` which does NOT exist. Claim is accurate but should carry an explicit `[CODE-VERIFIED]` tag. See IMPORTANT-4. |
| 5 | Contradiction resolution — no unresolved conflicts between researchers | FAIL | Two contradictions detected. (a) CRITICAL: file 02 line 117 says drop YAML / pyyaml in favor of JSON (`for v0.1 manifest, JSON is simpler`). Files 01, 03, 04, research-notes, and the spec §5 all use YAML (manifest.yaml). The spec OQ-1 at §16 recommends YAML; research-notes locks YAML; file 01 lists `PyYAML>=6.0` as a runtime dep (lines 911, 90). File 02 directly contradicts the rest of the cohort and the spec. (b) IMPORTANT: file 02 line 46 prescribes `src/ironops/cli/main.py` with per-command subpackage layout; file 01 §1.10 and research-notes line 134 prescribe `src/ironops/cli.py` single module. File 03 R6 references `cli.py`. Inconsistent CLI organization between cohort and reference patterns. See CRITICAL-1 and IMPORTANT-1. |
| 6 | Gap severity — flagged gaps correctly classified | FAIL | File 04 line 522 flags the rsync/git-push failure as a spec gap requiring a new `PUBLISH_FAILED` NFR-7 code. Recommendation is correct and aligned with spec §7 Stage 6. However file 04 buries this as a Recommendation rather than escalating it to a CRITICAL spec gap that must be resolved before builder implementation. File 01 §1.2 includes `PUBLISH_FAILED=18` in `ExitCode` enum — silently adding the missing code rather than flagging the spec gap. Net effect: the cohort silently extends the NFR-7 enum without surfacing the spec amendment requirement. See IMPORTANT-2. |
| 7 | Depth appropriateness — Standard tier: 30-50 documented files, multiple subprocess shapes, full template requirements | PASS | File 01 documents 47 files (within 30-50 range). File 04 documents 8 subprocess invocations (B.1–B.8) with full exit-code + stderr + failure-mode mapping. File 03 documents 11 template requirements R1–R11 covering frontmatter, sections D1–D3, B-series checklist rules, E/F/G/H/I/J/L/M section IDs. Depth meets Standard tier expectations. |
| 8 | Integration point coverage — git, claude validate, rsync, github push | PASS | File 04 §B.1–B.8 covers: B.1 git clone --depth=1, B.2 git rev-parse HEAD, B.3 git remote show origin, B.4 git status --porcelain on upstream, B.5 git status --porcelain on IronOps tree (FR-12 preflight), B.6 `claude plugin validate`, B.7 `rsync -a --delete`, B.8 git add/commit/push with no-changes-skip-empty-commit decision and rebase retry. All four spec integration points covered. |
| 9 | Pattern documentation — IronClaude reference patterns specific enough for adaptation | PASS | File 02 documents 12 numbered pattern groups with explicit "Adapt for IronOps" subsections and explicit non-copy enumeration (lines 923–933). File 02's "Adaptation Summary" §12 ranks the 12 highest-impact patterns. Patterns are concrete (named functions, exact subprocess shapes, exact code snippets) rather than abstract advice. |
| 10 | Incremental writing compliance — files show iterative structure | PASS | All four files exhibit incremental structure: section headers progressively numbered, subsection variations (e.g. file 02 has Pattern 1.1, 1.2, 2.1–2.6, 3.1–3.3, ...). File 02's "Status: In Progress" at top with "Status: Complete" at bottom further confirms incremental writing. No file appears one-shotted with perfect-from-start structure. |

## Summary

- Checks passed: 7
- Partial / Failed: 3 (#4 partial, #5 failed, #6 failed)
- Critical issues: 1
- Important issues: 4
- Minor issues: 3
- Issues fixed in-place: 0 (fix_authorization: false)

---

## Issues Found

| # | Severity | Location | Issue | Required Fix |
|---|----------|----------|-------|-------------|
| CRITICAL-1 | CRITICAL | research/02-ironclaude-reference-patterns.md §2.2 line 117 + §"Explicit non-copies" line 933 | File 02 prescribes dropping `pyyaml` and using JSON for the v0.1 manifest. This directly contradicts: spec §5 (YAML schema), spec §16 OQ-1 (YAML recommended), research-notes.md OQ-1 (YAML locked), file 01 §1.3 + §6.5 (manifest.yaml + PyYAML runtime dep), file 03 (no JSON references), file 04 (assumes `manifest.yaml` throughout). If the builder is implemented per file 02, the rendered manifest format will be incompatible with every other artifact. | Reconcile: file 02 must update §2.2 and the "Explicit non-copies" list to KEEP PyYAML for the v0.1 builder. The recommendation to drop YAML is wrong relative to the spec and the rest of the cohort. |
| IMPORTANT-1 | IMPORTANT | research/02-ironclaude-reference-patterns.md §1.2 + research/01-file-inventory.md §1.10 | File 02 prescribes a CLI subpackage layout (`src/ironops/cli/main.py` + per-command modules like `src/ironops/cli/build.py`). File 01 prescribes a single-module CLI (`src/ironops/cli.py`). Both layouts are defensible but the cohort must pick one before task-builder runs or the generated task file will have an inconsistent module tree. | Reconcile to single-module `src/ironops/cli.py` for v0.1 (matches file 01, simpler, only 3 subcommands per file 01 §1.10). File 02 should be updated to recommend subpackage layout as deferred future structure, not v0.1 baseline. |
| IMPORTANT-2 | IMPORTANT | research/04-test-and-integration-patterns.md §B.7 line 521-522 + §SUMMARY recommendation 1 (line 684) | The spec §7 Stage 6 PUBLISH and NFR-7 categorical codes do NOT include `PUBLISH_FAILED`. File 04 correctly identifies this gap but classifies it as a Recommendation. File 01 §1.2 silently adds `PUBLISH_FAILED=18` to the `ExitCode` enum. This silently amends the spec NFR-7 enum without an explicit spec-amendment item in the task file. | Either: (a) file 04 escalates this to a CRITICAL spec gap and the task-builder includes a spec-amendment item; OR (b) the cohort decides to map rsync/push failures to existing `VALIDATE_FAILED` semantics with a clarifying note. Current state is silent extension — unsafe. |
| IMPORTANT-3 | IMPORTANT | research/01-file-inventory.md (entire) vs spec §2.1 | Spec §2.1 says builder is `scripts/build_plugin.py` and helpers. File 01 prescribes `src/ironops/` package layout (10 modules, click console_script entry point). Spec §17 Definitions line 578 reinforces `scripts/` location: "the Python program in /config/workspace/IronOps/scripts/". The package layout in file 01 is a better engineering choice but it deviates from spec without flagging the deviation. | Either: (a) the cohort adds an explicit "deviation from spec §2.1 / §17: builder ships as a package not a script — rationale: testability + pyproject entry point" note in research-notes.md and the task file; OR (b) file 01 moves to `scripts/build_plugin.py` layout. Current state is silent deviation. |
| IMPORTANT-4 | IMPORTANT | research/04-test-and-integration-patterns.md §B.5 line 453 + research/01-file-inventory.md NONE | File 04 §B.5 introduces a `--allow-dirty` CLI flag to bypass the FR-12 BUILDER_DIRTY_TREE check for local dev. This flag has no spec basis (spec §3 FR-12 says "MUST exit with meaningful codes (0 = success, ≠0 = failure)"; spec §9 row 26 specifies the dirty-tree guard with no documented override). File 01 §1.10 cli.py does not list `--allow-dirty` as a build option. | Either: (a) drop the `--allow-dirty` flag from the cohort (file 04 should remove the recommendation); OR (b) add it to the spec as a documented override with audit-log behavior. Inventing flags not in the spec is scope creep that the builder agent might or might not pick up — non-deterministic. |
| MINOR-1 | MINOR | research/02-ironclaude-reference-patterns.md line 3 + line 937 | File 02 has `Status: In Progress` at the top of the file but `Status: Complete` at the bottom (line 937). One of them is wrong. | Update line 3 to `Status: Complete`. |
| MINOR-2 | MINOR | All four research files | Doc-derived claims are not tagged with `[CODE-VERIFIED]`, `[CODE-CONTRADICTED]`, or `[UNVERIFIED]` markers. The only file using the convention is research-notes.md (one tag at line 43). The convention helps the task-builder distinguish verified-from-code claims from speculation. | Future research files should adopt the tag convention. For this gate, file 02's claim about `build_superclaude_plugin.py` being broken should specifically carry a `[CODE-VERIFIED]` tag (verified by this QA against scripts/build_superclaude_plugin.py:15-22). |
| MINOR-3 | MINOR | research/01-file-inventory.md FR/NFR coverage table line 1167-1204 | NFR-3 (Plugin context cost budget — < 500 tokens always-on per spec §4) is not listed in the coverage table. There's no implementing module or test for context-cost measurement. | Add NFR-3 row: either implementing-module = none (measured at install time via `claude plugin details`) + test = manual, OR add a `tools/measure_context_cost.py` script and a CI step that reports the metric. |

---

## Critical Counter-Verifications Performed (Adversarial)

1. **File 02's `build_superclaude_plugin.py is broken` claim** — VERIFIED by reading `/config/workspace/IronClaude/scripts/build_superclaude_plugin.py:15-22`. The file declares `MANIFEST_DIR = PLUGIN_SRC / "manifest"` and `load_metadata()` reads `MANIFEST_DIR / "metadata.json"`. Neither the directory nor the file exists in the IronClaude tree. Claim is accurate. Verified.
2. **All 26 manifest entries' upstream paths exist** — VERIFIED via Bash loop over 11 agents + 8 skills + 7 commands in §13 shortlist. All 26 paths exist in IronClaude. Verified.
3. **MDTM template paths** — VERIFIED: `/config/workspace/IronClaude/src/superclaude/templates/workflow/02_mdtm_template_complex_task.md` exists (1204 lines); `.claude/templates/workflow/` contains only 03/04/05/06 templates, confirming research-notes' `[CODE-VERIFIED]` finding. Verified.
4. **Reference task TASK-RF-20260525-194356.md** — VERIFIED to exist (285 lines); spot-checked Phase 5 at lines 209-221 — matches researcher 03's exemplar verbatim. Verified.
5. **File 04's NFR-7 enum claim** — VERIFIED against spec §7/§9: spec NFR-7 lists 8 codes; rsync/push failure has no clean mapping; researcher 04's gap-flag is correct. Verified.
6. **Researcher 02 pyproject.toml citations** — VERIFIED lines 72-77 (`packages = ["src/superclaude"]`), 64-66 (`[project.scripts] superclaude = "superclaude.cli.main:main"`), 34-56 (dependencies block). All accurate. Verified.
7. **File 02's `cli/main.py:18-26` citation** — VERIFIED: `@click.group()` + `@click.version_option` + `def main()` exactly as cited. Verified.
8. **File 04's `conftest.py:38-44` "why session-scoped lives here" comment** — VERIFIED: comment block at lines 37-43 explains the pollution-snapshot fixture placement. Verified.

## Counter-Adversarial Self-Audit

If I told the user I found 0 issues, I would not believe that — there are CRITICAL inter-researcher contradictions visible from a side-by-side read of file 02 §2.2 (drop YAML, use JSON) against file 01 §6.5 (`manifest.yaml`, 140-line YAML example) and the spec §5 (YAML schema). Calling out this is the primary reason this report is FAIL not PASS.

Citable evidence of thorough verification:
- 4 research files Read in full (lines 1-1207 of file 01, 1-946 of file 02, 1-410 of file 03, 1-705 of file 04)
- research-notes.md Read in full
- Spec SPEC_IRONOPS_DEVOPS_PLUGIN.md Read in full (595 lines)
- 9 Bash spot-checks against IronClaude source: 26 manifest entry paths, pyproject.toml ranges, scripts/build_superclaude_plugin.py, sync_from_framework.py, cli/main.py, conftest.py, test_cli_registration.py, template path existence, .claude/templates/workflow contents
- 5 file:line citations independently verified

---

## Recommendations (resolve before proceeding to task-builder)

1. CRITICAL-1: Update file 02 §2.2 and "Explicit non-copies" to KEEP PyYAML for v0.1. Add a §2.2 note: "v0.1 manifest is YAML per spec §5 OQ-1; PyYAML is a runtime dep."
2. IMPORTANT-1: Decide CLI layout (recommend single-module `cli.py` per file 01); update file 02 §1.2 to match.
3. IMPORTANT-2: Escalate `PUBLISH_FAILED` to a CRITICAL spec gap; add a task item that updates spec NFR-7 (or maps to existing codes with explicit note).
4. IMPORTANT-3: Add explicit deviation note in research-notes.md: "Builder layout = src/ironops/ package (deviates from spec §2.1 scripts/build_plugin.py — rationale: pyproject console_script + testability)."
5. IMPORTANT-4: Drop the `--allow-dirty` flag from file 04, OR add it as a documented spec amendment item.
6. MINOR-1, 2, 3: documentation hygiene fixes.

After fixes, re-run research-gate QA (fix-cycle 2 of 3 per Retry Monotonicity Protocol). Expected |F_2| < |F_1|=8 issues. If `|F_2| >= 8`, emit `[HALT-MONOTONICITY] |F|=<n>`.

---

## Confidence Gate

- Checklist items: 10
- Verified: 10 (all checks evidenced by Read + Bash + Grep calls cited above)
- Unverifiable: 0
- Unchecked: 0
- Confidence: 10/10 = 100%
- Threshold: 95% — MET

**Confidence:** Verified: 10/10 | Unverifiable: 0 | Unchecked: 0 | Confidence: 100.0%
**Tool engagement:** Read: 6 | Grep: 1 | Glob: 0 | Bash: 6 | tavily_search: 0 | tavily_extract: 0 | web_search_fallback: 0 | web_fetch_fallback: 0

Tool count (13 calls) >= checklist item count (10) — review is not under-instrumented. No external (web) verification needed for this gate; all verification was source-truth-first against local files.

---

## QA Complete

Verdict: **FAIL** (8 findings: 1 CRITICAL + 4 IMPORTANT + 3 MINOR). Per gate rule "any gap regardless of severity = FAIL", builder must not proceed until all 8 are resolved or explicitly accepted as deviations. Report: this file.

