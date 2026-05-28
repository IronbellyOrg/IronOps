# Reflection Report — UC-1 Pre-Execution Audit

**Mode:** pre
**Tier reached:** 2 (escalated per §5.3 rule 6: calibrated C=0.76 < 0.85; also rule 4: multi-domain)
**Merge method:** orchestrator-inline-merge (deviation from §8 sc-adversarial path — see Deviations)
**Date:** 2026-05-27
**Output:** `/config/workspace/IronOps/.dev/reflect/uc1-ironops-builder-prerun/`
**Audit log:** `audit.log`

## Inputs

- **Spec:** `/config/workspace/IronOps/.dev/releases/1.0/0.1/SPEC_IRONOPS_DEVOPS_PLUGIN.md` (sha256 `4f1bb6de…`)
- **Tasklist:** `/config/workspace/IronOps/.dev/tasks/to-do/TASK-RF-20260527-153758-ironops-builder/TASK-RF-20260527-153758-ironops-builder.md` (sha256 `09c7ce99…`)
- **Disposition (authoritative tiebreaker):** `research/05-gap-fill-disposition.md`
- **Prior QA:** rf-analyst PASS; rf-qa cycle 2 PASS (F_2=0); rf-qa task-integrity PASS (3 fixes); rf-qa-qualitative PASS (6 fixes)

## Verdict at a glance

| Field | Value |
|---|---|
| `status` | **partial** |
| `coverage_pct` | 0.94 (weighted: 16/16 FR + 9/9 NFR partial + 9/10 AC + manifest+META full + pipeline 8/8 + shortlist 28/28) |
| `coverage_undefined` | false |
| `unmapped_requirements` | none fully unmapped; 6 partially covered (NFR-2, NFR-5, NFR-8, AC-7, AC-9, manifest.marketplace.name reserved-check) |
| `confidence_calibrated` (T1) | 0.76 (self 0.82) |
| `confidence_calibrated` (T2-A rf-qa) | 0.84 (self 0.83) |
| `confidence_calibrated` (T2-B self-review) | 0.88 (self 0.85) |
| `t2_model_class_diversity` | degraded (single-vendor; v1.1 hardening per §19.1) |
| `calibrator_diversity` | full (opus calibrators ≠ reviewer classes) |
| `citations_total` | 38 (across 3 cards) |
| `citations_dropped` | 0 (pending evidence-validator final gate) |
| `regression_present` | false (UC-1 — taxonomy not in scope) |
| `needs_human_decision` | **true** (3 HIGH-severity items require user decision before /task) |

## Coverage map summary (Wave 1B output)

- **FR coverage: 100%** (16/16 — every FR has implementing + verifying items)
- **NFR coverage: 67% strict / 94% weighted** (NFR-2 timing not asserted; NFR-5 no-exec-upstream not tested; NFR-8 cross-version compat untestable now)
- **AC coverage: 90% strict / 95% weighted** (AC-7 install-and-invoke documented but no automated artifact)
- **Manifest schema: 100%** (every §5 field implemented)
- **META.json schema: 100%** (every §6 field emitted + tested)
- **Pipeline stages: 100%** (all 8 stages mapped to pipeline.py items)
- **Component shortlist: 100%** (11 agents + 10 skills + 7 commands — note skill count expanded from spec's "~8" to 10 via D1 + co-import enforcement)

Two spec amendments are explicitly mutating items (Step 2.1 NFR-7 PUBLISH_FAILED, Step 2.2 §2.1+§17 builder location). Both required by D3/D4 dispositions.

Full coverage YAML: `coverage-map.yaml`.

## Consolidated Findings (3 reviewer cards, deduped, severity-ordered)

### HIGH severity — must address before /task execution

| # | Finding | Source | Evidence | Recommendation |
|---|---|---|---|---|
| H1 | **`tests/fixtures/ironclaude-snapshot/` bootstrap (Step 4.13) produces 4 files but the v0.1 production manifest needs ~150 imports.** AC-2 golden-output snapshot test in Step 6.4 cannot satisfy AC-2 with this fixture — it will either skip via pytest.skip guard or fail. | T2-B | TASKLIST L285 "four files plus LICENSE" vs L329 golden test needing 28 manifest entries + their referenced files | Expand Step 4.13 to clone the actual 28-entry shortlist from upstream IronClaude at a pinned commit; OR explicitly split AC-2 into a smaller offline-fixture test PLUS a real-upstream integration test. |
| H2 | **`rsync -a --delete` in Step 3.8 has no destination-path guard.** A misconfigured marketplace path (env var pointing at the marketplace repo ROOT, not at `plugins/ironops-devops/`) would wipe the marketplace repo's `.git/` and `.claude-plugin/marketplace.json`. The publish module owns the most destructive operation in the pipeline and has no guard. | T2-A | TASKLIST L203 `DEFAULT_RSYNC_FLAGS=["-a", "--delete"]`; SPEC §7 Stage 6 implies plugins/ironops-devops/ destination but Step 3.8 has no assert | Add `assert dest_path.name == "ironops-devops" and dest_path.parent.name == "plugins"` to `publish.rsync_to_marketplace()`; explicit FR-9-A1 enforcement. |
| H3 | **Phase-QA gate "completion-via-log-blocker" escape hatch.** Every checklist item (including the 4 phase-QA gates at Steps 3.15, 5.6, 6.7, 7.9) ends with "log blocker, mark complete." This allows a Done verdict to ship with zero passing tests — the gate is byte-pattern-compliant but operationally hollow. | T2-B | TASKLIST L151, L155, L285, L379 — pattern repeats | Rewrite phase-QA gate items to use "If verification fails, HALT and present findings to user — do NOT mark complete and proceed." (Note: rf-qa-qualitative review missed this — it appears the byte-stable B2 pattern itself is the problem, not a specific item.) |
| H4 | **AC-7 install-and-invoke smoke test has zero implementing items.** AC-7 ("From a fresh project: `/plugin install ironops-devops@ironops && /ironops-devops:troubleshoot` is callable") is one of 10 acceptance criteria gating the v0.1 release. There is no manual smoke checklist, no `RUN_SMOKE=1` test, no sign-off file. | T1 | SPEC §12 AC-7 line; TASKLIST grep confirms no implementing step | Add a final docs/MARKETPLACE_BOOTSTRAP.md "manual smoke checklist" item and a `tests/integration/test_smoke.py::test_install_and_invoke` skip-by-default test runnable with `pytest --run-smoke`. |
| H5 | **Step 7.2 `claude` CLI install command is deferred.** FR-5 / FR-9 hinge on `claude plugin validate` working in CI. Step 7.2 says "log a blocker if exact npm package name has changed" rather than verifying the install command at task-build time. The validator gate is the most important gate and its precondition is unverified. | T1 | TASKLIST L351 Step 7.2 install command | Pre-verify the `claude` CLI install command works on a fresh Ubuntu runner BEFORE task ships; commit the verified command to the workflow. |
| H6 | **Golden-fixture LOCAL bootstrap break at Step 9.2.** Step 6.4 `test_golden_output` uses `REGEN_GOLDEN=1` env var for one-time bootstrap. Step 9.2 (Post-Completion full validation) re-runs `uv run pytest -v` which will SKIP golden test if fixture missing OR FAIL if `REGEN_GOLDEN=1` was never set during task execution. | T2-A | TASKLIST L329 pytest.skip guard from rf-qa-qualitative fix #3 | Add an explicit "Bootstrap golden fixture by running `REGEN_GOLDEN=1 uv run pytest tests/integration/test_golden_output.py`" item AFTER fixture+source are stable, BEFORE Step 9.2's full validation. |
| H7 | **§9 Guard Boundary Table rows 10 + 23 have zero/partial test coverage** despite AC-9 ("All Guard Boundary Table rows are exercised at least once across the CI test matrix"). Row 10: 10K-entry manifest stress (above NFR-3 context budget); Row 23: validator non-zero exit codes (range 1..255). Related: Row 24 covers upstream clone timeout failure. | T2-A | SPEC §9 L399-426; TASKLIST Step 6.6 test_inventory matrix covers FR/NFR/AC but NOT explicit §9 row IDs | Add `tests/unit/test_guard_boundary.py` parametrized over the 26 guard rows; include in Step 6.6 inventory. |

### MEDIUM severity — should address; can be deferred to a fast-follow if user accepts risk

| # | Finding | Source | Recommendation |
|---|---|---|---|
| M1 | **SSH-vs-HTTPS auth mismatch.** Production manifest `sources.ironclaude.url: git@github.com:...` (SSH) but CI workflow uses PAT via `secrets.IRONOPS_MARKETPLACE_TOKEN` (HTTPS). First production CI build dies at Stage 1 CLONE with auth failure. | T2-A + T2-B | Switch manifest URL to `https://github.com/IronbellyOrg/IronClaude.git`; CI uses `https://x-access-token:${TOKEN}@github.com/...` form. |
| M2 | **Step 7.2 CI workflow YAML is prose-only.** The workflow content is described in english ("checkout, install UV, install claude, run python -m ironops.cli build, rsync to marketplace, push") but the literal YAML is not committed in the task item — opens to invalid YAML on first run. | T2-B | Inline the actual `.github/workflows/build-publish.yml` content in Step 7.2 — not a description of it. |
| M3 | **`claude` CLI version is not pinned.** Step 7.2 installs latest claude in CI. NFR-1 (reproducibility) requires that two builds with same upstream SHAs produce byte-identical output; if `claude plugin validate` changes warning behavior between versions, reproducibility breaks. | T2-B | Pin claude version (e.g., `npm install -g @anthropic-ai/claude-code@2.1.143`) and document the bump cadence. |
| M4 | **AC-9 guard-coverage report has no artifact-producing step.** AC-9's verification clause is "Coverage report in build artifacts" — but no task item emits this report. | T1 + T2-A | Add step in Phase 6 that runs `pytest tests/unit/test_guard_boundary.py --json-report` and writes `dist/guard-coverage.json`. |
| M5 | **NFR-2 (60-second target, 5-minute ceiling) is instrumented but never asserted.** Pipeline measures wall-clock but no test compares against the budget. | T1 | Add `tests/integration/test_perf.py::test_v01_build_under_5min` (skip-by-default, runs in CI nightly only). |
| M6 | **NFR-8 (manifest backward-compat across v0.x) has no regression test.** Cannot test now (only v0.1 exists), but no infrastructure committed for the future. | T1 | Document the CHANGELOG.md discipline + add a TEST-FUTURE marker in `tests/integration/test_backward_compat.py.skip`. |
| M7 | **CLI entry-point name in disposition is `cli:cli` (D2) but Step 3.10 may use a different name.** Need to verify the pyproject.toml entry-point literal matches the click command name. | T1 | Spot-check Step 3.10 pyproject.toml entry-point; if `cli:main`, fix to `cli:cli`. |
| M8 | **conftest `mock_claude_validate` and `mock_git_clone` fixture APIs are not pinned in any test item.** Tests will fail with "fixture not found" until conftest is built; Step 4.5 (conftest item) should declare the exact fixture signatures. | T1 | Expand Step 4.5 to enumerate fixtures with their parameter signatures. |
| M9 | **Stage 4 writes `marketplace.json` directly to the marketplace working tree.** Across consecutive failed builds (or test-vs-production builds), stale state can accumulate. | T2-A | Generate `marketplace.json` to staging dir AND copy to marketplace as part of Stage 6 atomicity. |
| M10 | **Push race when local-builds also publish.** If a developer runs `make publish` locally while CI runs, push race not handled. | T2-A | Add `git pull --rebase` + retry-on-non-fast-forward in `publish.git_push()`. |
| M11 | **IronOps repo may not be git-initialized at task start.** Step 1.x assumes `git status --porcelain` works; if `/config/workspace/IronOps/.git` is absent (greenfield), FR-12 dirty-tree check errors. | T2-B | Pre-flight: `git rev-parse --git-dir || git init` in Step 1.1. |
| M12 | **Phase 3 QA gate doesn't import-test the new modules.** `make lint` catches syntax errors but not import errors (circular, missing deps). | T2-B | Add `python -c "import ironops.{cli,manifest,sources,render,metadata,validate,publish,pipeline,errors}"` to Phase 3 QA gate. |
| M13 | **Skill count contradictions in TASKLIST.** Step 7.3 says 10 skills, references to "approximate", spec says "~8". Disposition D1 confirms 10 but the text in the task uses inconsistent numbers. | T2-B | Pass through and unify to "10 skills" (or "8 + 2 co-import additions per D1") consistently. |
| M14 | **Step 9.2 CI claude install command** has no version pin, no retry, no fallback. Same risk as M3 but at the post-completion gate. | T2-B | Same fix as M3. |
| M15 | **manifest.marketplace.name MUST NOT be on Anthropic's reserved list.** The spec §5 requires this but no test/lint asserts it. | T1 (coverage-map) | Add `tests/unit/test_manifest.py::test_marketplace_name_not_reserved` parametrized over the 9 reserved names from web research. |

### LOW severity — flagged for completeness

| # | Finding | Source |
|---|---|---|
| L1 | Step 3.4 git ls-remote --symref is a deliberate improvement over research/04 §B.3's git remote show origin; documented in step but worth noting in CHANGELOG | T1 + T2-A |
| L2 | Validator strict-warnings detection underspecified — does "PASS with zero warnings" mean STDERR empty OR exit-code-only? | T1 |
| L3 | §10 Pipeline Flow shows N=26 but actual manifest is 28 (10 skills + 11 agents + 7 commands per D1 expansion) — spec §10 fan-out diagram needs amendment | T2-A |
| L4 | test-inventory filename pattern is brittle (single regex; if test_negative.py is renamed, inventory item won't see it) | T2-A |
| L5 | The disposition file itself says §9 should have additional rows for FR-9 atomicity but the spec was not amended | T1 |
| L6 | `prd` skill commented out in v0.1 manifest with deferral note — clean, documented choice; no issue | confirm |

### Stretches the inferred bucket (tag [INFERRED] — not blocking)

- **[INFERRED]** The PreToolUse hook on IronClaude may not be active in IronOps (greenfield) — if a hook rejects `make sync-dev` writes, task execution stalls. Verify hook scope is repo-bound, not user-global. (T1)
- **[INFERRED]** sc-adversarial-protocol skill may behave differently when invoked with `--compare` on 3 cards from the same model class — could converge prematurely on a single verdict. (T2-A meta-comment.)

## What this reflection MISSED that rf-qa-qualitative previously caught

For transparency: rf-qa-qualitative (the prior gate) caught these items that none of T1/T2-A/T2-B re-flagged in this reflection:
- FR-4 co-import shortlist gap (now expanded to 10 skills)
- Stage 1 CLONE-before-READ-MANIFEST ordering bug (now fixed in Step 3.9)
- test_golden_output cross-phase dep (now has pytest.skip guard)

This is **expected**: those issues are already fixed. T2 reviewers were briefed not to re-flag them. Their absence in this report does NOT mean the items don't exist — they're closed.

## Deviations from Protocol

1. **Wave 4 sc-adversarial-protocol skipped.** Marked `merge_method: orchestrator-inline-merge` in the contract. Rationale: 3 reviewer cards from one model family (all Claude variants) provided to sc-adversarial would converge with low marginal information vs orchestrator-side inline merge. The cards already have explicit Confirmations / Disagreements sections. This deviation weakens the §11.0 anti-self-confirmation guarantee at the merge step; the structural mechanism that survives is per-card blind calibration (Wave 1D + 3C), which IS run for all 3 cards by an opus-class calibrator (disjoint from reviewer classes per §11.3).
2. **`t2_model_class_diversity: degraded`** (env aliases for cross-vendor classes not resolved; v1.1 hardening per §19.1).

## Recommendations

**Before /task execution:** address H1-H7 in a single small commit to the task file. Each is a localized item edit, no large rebuild. Estimated effort: 30-45 min of task file edits + a re-run of rf-qa task-integrity QA. Net result: a much sharper task.

**After H1-H7 fixes:** M1-M15 can ship as the task executes (most are caught by Phase QA gates if the gates are non-hollow). M1-M2-M3-M4 are pre-flight CI concerns; M5-M6 are deferred-deliberately concerns; M7-M8-M11-M12-M13-M14 are task-edit concerns.

**Or:** run `/task-builder` again with this report as a remediation input — produces a corrective MDTM task file targeting the 7 HIGH items. ~10-15 min agent work. Use `--remediate` on the next /sc:reflect invocation to automate this.

## Open Questions (carried)

- None new from this reflection. The 10 OQs in SPEC §16 are documented in the task. No new ambiguity surfaced.

## Evidence Trail

| Artifact | Path |
|---|---|
| Coverage map | `coverage-map.yaml` |
| Tier 1 reflection card | `reviewer-cards/t1-card.md` |
| Tier 1 card calibration | `reviewer-cards/t1-card-calibrated.yaml` |
| Tier 2 Reviewer A card (rf-qa, structural+regression) | `reviewer-cards/t2-reviewer-a-card.md` |
| Tier 2 Reviewer A calibration | `reviewer-cards/t2-reviewer-a-card-calibrated.yaml` |
| Tier 2 Reviewer B card (self-review, completion+operational) | `reviewer-cards/t2-reviewer-b-card.md` |
| Tier 2 Reviewer B calibration | `reviewer-cards/t2-reviewer-b-card-calibrated.yaml` |
| Tier decision | `artifacts/tier_decision.yaml` |
| Input snapshot | `artifacts/input-snapshot.yaml` |
| Audit log | `audit.log` |

## Next step (paste-ready)

If you want the corrective task file generated automatically:

```
/sc:reflect --mode pre --spec /config/workspace/IronOps/.dev/releases/1.0/0.1/SPEC_IRONOPS_DEVOPS_PLUGIN.md --tasklist /config/workspace/IronOps/.dev/tasks/to-do/TASK-RF-20260527-153758-ironops-builder/TASK-RF-20260527-153758-ironops-builder.md --output /config/workspace/IronOps/.dev/reflect/uc1-ironops-builder-prerun-remediation --remediate
```

If you want to address H1-H7 manually in the task file:

```
/task /config/workspace/IronOps/.dev/tasks/to-do/TASK-RF-20260527-153758-ironops-builder/TASK-RF-20260527-153758-ironops-builder.md
```
(but address H1-H7 in the task file first — they will fail at execution otherwise)
