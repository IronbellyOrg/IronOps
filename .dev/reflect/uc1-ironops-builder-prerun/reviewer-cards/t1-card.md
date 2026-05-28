# Tier 1 Reflection Card — UC-1 Pre-Execution Audit

**Status:** Complete
**Mode:** pre
**Date:** 2026-05-27
**Reviewer:** root-cause-analyst (Tier 1, single-agent)
**Inputs:** SPEC, TASKLIST, disposition, prior QA

## 1. What the task aims to do (one paragraph)

The task implements v0.1 of the IronOps DevOps Claude Plugin builder as a greenfield Python package at `/config/workspace/IronOps/src/ironops/`. The builder consumes a YAML manifest (`manifest.yaml`), shallow-clones declared upstream Git repositories at HEAD (resolving default branches via `git ls-remote --symref`), renders a curated Claude Code plugin tree to a staging directory while enforcing co-import (FR-4) and path-safety (FR-8) guards, emits provenance metadata (`plugin.json`, `META.json`, `THIRD_PARTY_LICENSES.md`, `.claude-plugin/marketplace.json`), validates the staging tree via `claude plugin validate`, and atomically publishes the validated tree to `IronbellyOrg/ironops-marketplace` via rsync + git commit/push. The 62-item, 8-phase tasklist sequences scaffolding, two explicit spec amendments (NFR-7 + §2.1/§17), 10 Python modules, 7 manifest fixtures + hermetic snapshot, unit tests, integration tests, CLI tests, two CI workflows, the v0.1 production manifest, and four docs.

## 2. Strengths (≤5 bullets — don't rubber-stamp; only call out genuine strengths)

- **Spec amendments are encoded as discrete checklist items, not silent extensions** — Phase 2 Steps 2.1 and 2.2 (TASKLIST L165, L169) explicitly Edit the spec for `PUBLISH_FAILED` and `src/ironops/` package layout per dispositions D3 and D4. Grounded.
- **FR-4 co-import production-manifest pre-check completed** — Step 7.3 (TASKLIST L355) lists 10 skills including `sc-cleanup-audit-protocol` and `sc-task-protocol`, derived from prior QA's grep of upstream `cleanup-audit.md`/`task.md` (qa-qualitative-review.md L50). The §13 spec text remains `~8` (SPEC L520), so the manifest is fortified against a runtime FR-4 failure that the spec alone would not have prevented. Grounded.
- **Chicken-and-egg ordering between Stage 1 CLONE and Stage 2 READ MANIFEST is explicitly resolved** — Step 3.9 (TASKLIST L207) documents that `manifest.load_manifest` runs at the START of Stage 1, with Stage 2 treated as a re-validation no-op for spec-traceability. Grounded.
- **NFR-7 9th categorical code (`PUBLISH_FAILED`) flows through errors.py → CLI → tests consistently** — Step 3.2 (L179) defines the enum, Step 3.10 (L211) consumes it via `sys.exit(int(result.exit_code))`, Step 5.1 (L291) parametrizes the test over all 9 codes, Step 6.3 (L325) verifies categorical exit codes per fixture. Grounded.
- **Hermetic fixture strategy is concrete** — Step 4.13 (L285) copies a documented IronClaude subset (4 files + LICENSE) into `tests/fixtures/ironclaude-snapshot/` and pins the source SHA in `README.md`; Step 4.5 conftest builds the `ironclaude_fixture_repo` via `git init` at test time. Grounded.

## 3. Findings — Coverage Gaps

### Finding 3.1 — AC-7 (install-and-invoke smoke test) has NO implementing or verifying item [HIGH]

**Evidence:** SPEC §12 L507 specifies AC-7: "From a fresh project: `claude plugin marketplace add IronbellyOrg/ironops-marketplace && claude plugin install ironops-devops@ironops && /reload-plugins`, then `/ironops-devops:troubleshoot` is callable. | Manual smoke test". Grep across TASKLIST for `AC-7`, `/reload-plugins`, `claude plugin install ironops-devops@`, `nightly`, `smoke test`, and `install-and-invoke` returns ZERO hits in any checklist item. SPEC §14 L542 also lists "Smoke: install-and-invoke" as a test class. Grounded.

**Spec ref:** AC-7 (SPEC L507), Test Strategy §14 row "Smoke: install-and-invoke" (SPEC L542).

**Severity:** HIGH — AC-7 is one of 10 acceptance criteria; AC-8 (test inventory mapping) cannot be honestly populated if AC-7 has no test referent. The "Definition of Done" at SPEC §12 says all 10 ACs must be satisfied for v0.1 release.

**Recommendation:** Add a discrete Phase 7 or Post-Completion item that either (a) defines a manual smoke checklist with a sign-off file under `phase-outputs/reviews/ac7-smoke-signoff.md`, or (b) creates a `tests/integration/test_smoke_install.py` skipped-by-default test gated behind `RUN_SMOKE=1` env var that invokes a fresh ephemeral project, runs the documented `claude plugin marketplace add` + `claude plugin install` + `/reload-plugins` sequence against the build output, and asserts `/ironops-devops:troubleshoot` resolves.

### Finding 3.2 — AC-9 (Guard Boundary Table coverage report) has NO explicit verifier [MEDIUM]

**Evidence:** SPEC §12 L509 specifies AC-9: "All Guard Boundary Table rows are exercised at least once across the CI test matrix. | Coverage report in build artifacts". SPEC §9 (L399-426) enumerates 26 guard rows. TASKLIST Key Objectives §5 (L77) mentions "covering every FR/NFR/guard-boundary row from spec §9" as a goal but no Phase 6 or Phase 7 step generates a `phase-outputs/reports/guard-boundary-coverage.md` mapping each §9 row → test name, and no Step writes such a coverage report to "build artifacts" as AC-9 demands. Grounded.

**Spec ref:** AC-9 (SPEC L509), §9 Guard Boundary Table (SPEC L397-426).

**Severity:** MEDIUM — AC-9 verification phrase "Coverage report in build artifacts" is a concrete output requirement; without an item that produces this artifact, the executor will silently skip it.

**Recommendation:** Either extend Step 6.6 (`tests/test_inventory.md`) to add a "Guard Boundary Coverage" section mapping each of §9's 26 rows to a test function, OR add a new Phase 6 step that generates `phase-outputs/reports/guard-boundary-coverage.md` from the §9 table cross-referenced with test names, AND register this artifact in the `.github/workflows/test.yml` `upload-artifact` step.

### Finding 3.3 — NFR-2 (build wall-clock budget) implementation is documented but never measured/verified [MEDIUM]

**Evidence:** Step 3.9 (TASKLIST L207) states pipeline.py has "timing instrumentation warning at 60s soft and failing at 300s hard per NFR-2". There is NO test in Phase 5/6 that asserts the timing instrumentation actually exists in the module or that it triggers, AND no Phase 6 step measures actual full-build wall-clock against the 60s soft / 300s hard targets. Grep for `NFR-2`, `60 seconds`, `5 minutes`, `wall-clock`, `timing` across test steps returns no implementing tests. Grounded.

**Spec ref:** NFR-2 (SPEC L222), AC-1 (SPEC L501).

**Severity:** MEDIUM — A timing budget that is implemented but never validated is indistinguishable from one that is implemented incorrectly.

**Recommendation:** Add a Phase 6 integration test `test_timing.py` (or extend `test_pipeline.py`) that runs the full build against the snapshot fixture and asserts elapsed wall-clock is under both budgets, plus a unit test that monkeypatches `time.time()` to simulate stage durations exceeding 300s and asserts the build fails with a documented categorical code (the spec is silent on which NFR-7 code applies — clarify before merging).

### Finding 3.4 — NFR-8 (manifest schema backward-compat) has NO regression test [MEDIUM]

**Evidence:** SPEC §NFR-8 (L246) states `schema_version: "1"` manifests MUST continue to build through all v0.x releases. TASKLIST Step 7.7 (L371) mentions tracking schema_version bumps in CHANGELOG, but there is NO regression test that locks in the v0.1 schema acceptance contract for future versions. The `good.yaml` fixture (Step 4.6 L257) tests the current schema but not the locked-forward backward-compat invariant. Grounded.

**Spec ref:** NFR-8 (SPEC L246-247), FR-14 (SPEC L194-198).

**Severity:** MEDIUM — Forward NFR-8 enforcement is impossible in v0.1, but a "do not change schema_version semantics without an explicit major bump" lock is feasible via a frozen-fixture test.

**Recommendation:** Add a test fixture `tests/fixtures/manifests/v0_1_locked.yaml` and a test that asserts it parses successfully and emits the documented v0.1 fanout — this becomes the v0.1 acceptance contract for NFR-8 in v0.2+.

### Finding 3.5 — Spec amendment §17 wording underspecified in Step 2.2 [LOW]

**Evidence:** Step 2.2 (TASKLIST L169) edits SPEC §17 "Builder" definition. SPEC §17 L578 currently reads: "**Builder:** the Python program in `/config/workspace/IronOps/scripts/` that consumes `manifest.yaml` and produces the rendered plugin tree." Step 2.2 instructs the executor to make §17 read "consistently with the same package layout (with `scripts/` reserved for future helper scripts only)" — but does NOT supply the literal post-amendment text. Step 2.1 (NFR-7) similarly has no literal post-amendment text. Grounded.

**Spec ref:** SPEC §17 L578, disposition D4 (L83).

**Severity:** LOW — A diligent executor will produce sensible text, but two reviewers may produce divergent wording, which complicates the AC-8 traceability matrix (Step 6.6 references spec sections by content).

**Recommendation:** Pre-write the exact replacement strings in Step 2.1 and Step 2.2 so the Edit operation is mechanical. Example for §17: `"**Builder:** the Python package at /config/workspace/IronOps/src/ironops/, installable via uv pip install -e . with entry point ironops, that consumes manifest.yaml and produces the rendered plugin tree. The scripts/ directory is reserved for future helper scripts only."`

## 4. Findings — Ambiguity & Missing Verification

### Finding 4.1 — Step 3.10 + Step 3.11 entry-point name contradicts disposition D2 literal wording [MEDIUM]

**Evidence:** Disposition D2 (research/05-gap-fill-disposition.md L41) states verbatim: "Entry point in `pyproject.toml` is `ironops = \"ironops.cli:cli\"`." Step 3.10 (TASKLIST L211) prescribes "the entry point is `ironops = \"ironops.cli:main\"` (matching pyproject.toml registration in Step 3.11)" and defines `def main()` as a wrapper. Step 3.11 (L215) registers `scripts ironops="ironops.cli:main"`. Both Step 3.10 and Step 3.11 agree internally, but they contradict D2's literal direction. Grounded.

**Spec ref:** Disposition D2 (research/05 L41).

**Severity:** MEDIUM — D2 is the AUTHORITATIVE tiebreaker per the task framing ("MUST treat this file as the tiebreaker"). The current tasklist silently overrides it. A `main()` wrapper is fine engineering, but the deviation needs explicit acknowledgement in the disposition or the task — otherwise a future audit comparing tasklist to D2 will flag this as drift.

**Recommendation:** Either (a) update Steps 3.10/3.11 to use `ironops.cli:cli` per D2 literal (`main()` is unnecessary because `click.group()` is already callable as an entry point), OR (b) add a one-line note in Step 3.10 explicitly acknowledging "deliberate deviation from D2 literal: D2 prescribes `cli:cli`; we use `cli:main` as a wrapper to expose a Python-callable `main()` for testing and to centralize sys.exit translation. Both shapes satisfy the disposition's intent."

### Finding 4.2 — Step 3.10 `@click.version_option` and `version()` subcommand are redundant [LOW]

**Evidence:** Step 3.10 (TASKLIST L211) instructs both `@click.version_option(version=__version__, prog_name="IronOps")` on the group AND `@cli.command() def version()` printing `__version__` plus git SHA. Click already provides `--version` flag via `version_option`. The intent of the `version()` subcommand is plausibly that it adds the git SHA which `version_option` does not — but the task does not state which output is canonical for AC-1's "exit 0" verification or for the CLI test in Step 6.5. Grounded.

**Spec ref:** N/A (implementation choice).

**Severity:** LOW — Users will see two ways to query version, which is confusing but not blocking.

**Recommendation:** Decide: drop one or document that `--version` returns the package version and `version` subcommand returns version + builder SHA. Add a Step 6.5 test asserting both behaviors.

### Finding 4.3 — Step 3.7 "NFR-4 strict-warnings" detection is underspecified [MEDIUM]

**Evidence:** Step 3.7 (TASKLIST L199) instructs `validate.py` to "raise `ValidateFailed` when exit_code != 0 OR when stdout/stderr contains warning patterns (NFR-4 strict-warnings)" — but does NOT specify what those warning patterns are. NFR-4 (SPEC L230) says "zero errors and zero warnings"; `claude plugin validate` output format is not documented in the spec or research files. Grep across TASKLIST for "warning pattern" returns this single ambiguous reference. Grounded.

**Spec ref:** NFR-4 (SPEC L230), FR-5 (SPEC L121).

**Severity:** MEDIUM — A literal-string scan ("WARN" / "warning") is fragile; a structured exit-code check is more reliable. Without specification, the executor must guess, and the executor's guess will become the de facto contract.

**Recommendation:** Either (a) restrict the gate to `exit_code != 0` only (matching FR-5 literal text "non-zero exit MUST abort publish") and treat NFR-4 zero-warnings as a downstream code-review concern, OR (b) specify the warning patterns in Step 3.7 (e.g., `["WARNING:", "WARN:", "WARN ", "deprecated"]` — but this needs verification against actual `claude plugin validate` output).

### Finding 4.4 — Step 4.5 conftest.py `mock_claude_validate` is named but not specified [LOW]

**Evidence:** Step 4.5 (TASKLIST L253) lists `mock_claude_validate` as a fixture that "controls validator return code" but does not specify its API surface (does it monkeypatch `subprocess.run`? Replace `validate.run_validator`? Take a return-code parameter or a per-test param?). Step 6.1 (L317) uses `mock_claude_validate` without further clarification. Step 6.5 (L333) similarly. Grounded.

**Severity:** LOW — Sensible defaults are knowable, but two executors may produce incompatible fixtures.

**Recommendation:** In Step 4.5, specify the fixture signature: `@pytest.fixture def mock_claude_validate(monkeypatch): def _set(exit_code=0, stdout="", stderr=""): monkeypatch.setattr("ironops.validate.run_validator", lambda *a, **k: ValidatorResult(exit_code, stdout, stderr, 0.1)); return _set` — tests then call `mock_claude_validate(exit_code=1)` to inject failures.

## 5. Findings — Execution-Time Risks (will-this-actually-build-green concerns)

### Finding 5.1 — Step 7.2 claude CLI install command is unresolved at task-build time [HIGH]

**Evidence:** Step 7.2 (TASKLIST L351) instructs the workflow to "install claude CLI step (using `npm install -g @anthropic-ai/claude-code` or the current install command — log a blocker in Phase 7 findings if the exact npm package name has changed and resolve before merging the CI workflow)". The task explicitly accepts an unresolved install command as deferred to executor discretion. Grounded.

**Spec ref:** FR-5 (SPEC L121), AC-3 (SPEC L503).

**Severity:** HIGH — `claude plugin validate` is the gate that determines publish success (FR-5 + FR-9). If the install command in CI is wrong, the entire build pipeline fails at Stage 5 in EVERY production build until fixed. The "log a blocker" instruction defers the resolution to runtime rather than verifying at task-build time.

**Recommendation:** Resolve the claude CLI install command BEFORE execution starts. Either (a) verify the npm package via `npm view @anthropic-ai/claude-code` and pin the exact command, OR (b) document an alternative installer (e.g., curl-piped install script) AND verify it works on `ubuntu-latest`. Update Step 7.2 to remove the "log a blocker" escape hatch.

### Finding 5.2 — Step 4.13 hermetic snapshot may be insufficient for Step 5.3 default-branch test [MEDIUM]

**Evidence:** Step 5.3 (TASKLIST L299) tests `_resolve_default_branch` by monkeypatching `subprocess.run` to inject `git ls-remote --symref` stdout returning `"ref: refs/heads/develop"` — to verify "no hardcoded main/master". This is a UNIT test using monkeypatch, fine. But Step 6.1 (`test_pipeline.py` integration) runs the real pipeline against `ironclaude_fixture_repo` (a `git init`-based fixture per Step 4.5 conftest L253 + Step 4.13 L285). A locally-init'd git repo has NO remote, so `git ls-remote --symref <url> HEAD` against `file://<path>` returns NOTHING for HEAD symref because local repos initialized with `git init` may not have HEAD symbolic by default (default branch name varies by git version: `master` in older git, `main` in newer git after `init.defaultBranch` config). Grounded — verified via git documentation behavior knowledge; [INFERRED] regarding exact git version on CI runner.

**Spec ref:** FR-2-A3 (SPEC L102-103) "MUST resolve the upstream's default branch programmatically".

**Severity:** MEDIUM — Step 6.1 integration tests may either pass (if `mock_git_clone` short-circuits the resolver) or fail with `UpstreamCloneFailed` in ways unrelated to the FR being tested.

**Recommendation:** Step 4.5 conftest's `ironclaude_fixture_repo` should explicitly run `git symbolic-ref HEAD refs/heads/main` (or `develop`) after `git init` to guarantee a stable HEAD symref. Document this in the conftest step. Additionally, `mock_git_clone` in conftest should also short-circuit `_resolve_default_branch` to return a deterministic branch name so integration tests don't depend on git version behavior.

### Finding 5.3 — Step 6.3 induced-failure modes for VALIDATE_FAILED and BUILDER_DIRTY_TREE are vague [MEDIUM]

**Evidence:** Step 6.3 (TASKLIST L325) covers 10 categorical exit codes; for `VALIDATE_FAILED` it instructs "induced by tampering with the staging output between metadata and validate stages" and for `BUILDER_DIRTY_TREE` "induced via monkeypatch". The "tampering" mechanism is not specified — between Stage 4 and Stage 5 the staging dir is owned by the pipeline; tampering requires intercepting after Stage 4 completes, which monkeypatch alone may not enable (Stage 5 runs in the same `run_build` call). For `UPSTREAM_CLONE_FAILED` "induced via mock_git_clone raising" is fine if `mock_git_clone` supports that API — but Step 4.5 (L253) does not specify a `raise=True` parameter for `mock_git_clone`. Grounded.

**Severity:** MEDIUM — Tests that need to inject mid-pipeline failures are notoriously hard to write reliably; ambiguous specs lead to flaky tests or skipped failure paths.

**Recommendation:** For `VALIDATE_FAILED`: configure `mock_claude_validate(exit_code=1)` per Finding 4.4's signature instead of tampering. For `BUILDER_DIRTY_TREE`: monkeypatch `subprocess.run` to return non-empty `git status --porcelain` output when called from `_resolve_builder_version`. For `UPSTREAM_CLONE_FAILED`: extend `mock_git_clone` fixture API to accept a `raise_with` parameter. Update Step 4.5 conftest spec accordingly.

### Finding 5.4 — Step 5.4 path-escape parametrize list includes Windows paths but builder runs on Linux only [LOW]

**Evidence:** Step 5.4 (TASKLIST L303) parametrizes path-escape rejection over `["../../etc", "/etc/passwd", "C:\\Windows", "..\\..\\windows"]`. NFR-1 (SPEC L219) constrains the builder to "Linux x86_64". Step 4.5 conftest fixtures + Step 7.1 CI matrix do not test on Windows. The Windows path variants test the path-safety regex but the regex's actual behavior on Windows-style paths in a Linux-only builder is questionable — `C:\\Windows` may or may not match path-escape depending on regex shape. Grounded.

**Severity:** LOW — Defensive coverage is reasonable, but if the regex doesn't naturally catch Windows paths and the executor adds Windows handling solely for the test, that's added complexity for a hypothetical attack surface.

**Recommendation:** Either keep the Windows paths in the parametrize list AND document the expected regex behavior, OR drop them as out-of-scope for a Linux-only v0.1 builder.

### Finding 5.5 — Step 6.4 golden-fixture REGEN_GOLDEN bootstrap creates a chicken-and-egg in CI [MEDIUM]

**Evidence:** Step 6.4 (TASKLIST L329) implements golden snapshot with `REGEN_GOLDEN=1` bootstrap pattern: on first run the JSON is written and assertion skipped; subsequent runs diff against the JSON. Step 6.7 (L341) Phase 6 QA gate allows one-time REGEN. Step 9.2 (L403) runs final validation. AC-2 (SPEC L502) requires snapshot test PASS. In CI (`.github/workflows/test.yml` Step 7.1), the golden JSON must be committed to the repo BEFORE the CI run, but the tasklist sequencing doesn't include an explicit "commit golden JSON before pushing branch for CI" item. Grounded.

**Spec ref:** AC-2 (SPEC L502).

**Severity:** MEDIUM — First CI run will FAIL because golden JSON doesn't exist; second CI run needs the JSON committed but Step 9.2 doesn't sequence the commit operation.

**Recommendation:** Add a Phase 7 step or sub-step in Step 6.4/6.7 that says: "After first successful local REGEN_GOLDEN run, commit `tests/fixtures/golden/v0_1_plugin_tree.json` to the repo BEFORE pushing the branch. CI will fail otherwise."

### Finding 5.6 — Step 3.6 `_resolve_builder_version` reads from `<ironops-repo-root>` but path is not parameterized [LOW]

**Evidence:** Step 3.6 (TASKLIST L195) instructs `_resolve_builder_version()` to invoke "`git -C <ironops-repo-root> rev-parse HEAD` and `git status --porcelain`". The path `<ironops-repo-root>` is presented as a placeholder; the function signature shown is `_resolve_builder_version()` with no parameters. Step 3.9 (L207) Stage 0 calls `metadata._resolve_builder_version`. The implementation must resolve the repo root — likely via `__file__`-based path resolution or a hardcoded `/config/workspace/IronOps/` — but the task does not specify. Hardcoding the path will break in CI (where the repo lives in a runner-specific path like `/home/runner/work/...`). Grounded.

**Spec ref:** FR-12 (SPEC L174-181), FR-6 (SPEC L130-135).

**Severity:** LOW (in dev) / MEDIUM (in CI) — Easy to fix; risky if missed.

**Recommendation:** Specify in Step 3.6 that `_resolve_builder_version()` accepts an optional `repo_root: Path | None = None` parameter and defaults to `Path(__file__).resolve().parent.parent.parent` (relative to `src/ironops/metadata.py`). Add a corresponding unit test in Step 5.5 that monkeypatches the path.

## 6. Findings — Spec / Tasklist Contradictions

### Finding 6.1 — §13 shortlist "~8 skills" vs Step 7.3 "10 skills" remains a spec-vs-tasklist inconsistency [LOW]

**Evidence:** SPEC §13 (L520) lists "Skills (~8)" naming 8 skills. Prior QA (qa-qualitative-review.md L33, L50) expanded to 10 skills to satisfy FR-4 co-import for `cleanup-audit` and `task` commands, and this is reflected in Step 7.3 (TASKLIST L355). The prior QA recommendation L104 explicitly says "if the spec is interpreted strictly, the §13 shortlist should be amended to list 10 skills. Optional follow-up amendment in a future revision." There is NO Phase 2 amendment item that updates §13 to match. Grounded.

**Spec ref:** SPEC §13 L520, prior QA recommendation L104.

**Severity:** LOW — Spec wording says "~8" (approximate) which legitimizes 10, but the AC-8 traceability matrix in Step 6.6 may flag the divergence.

**Recommendation:** Either add a third spec-amendment item in Phase 2 to update §13 to "Skills (10)" listing the 10 skills explicitly, OR add a one-line note to Step 7.3 acknowledging the §13 "~8" is approximate and the manifest's 10 satisfies it. (The prior QA noted this as optional — but if AC-8 verification will check spec wording literally, this becomes load-bearing.)

### Finding 6.2 — Spec §UC-3 trigger sequence omits `/reload-plugins` but AC-7 includes it [LOW]

**Evidence:** SPEC §UC-3 (L42-44) lists the install sequence as `claude plugin marketplace add ... && claude plugin install ironops-devops@ironops → /ironops-devops:troubleshoot is callable`. AC-7 (L507) adds `&& /reload-plugins` between install and invoke. The spec is internally inconsistent on whether `/reload-plugins` is required. This is not a tasklist bug per se but it propagates ambiguity to any AC-7 verifier added per Finding 3.1. Grounded.

**Spec ref:** SPEC §UC-3 L42-44, AC-7 L507.

**Severity:** LOW — Minor spec internal inconsistency.

**Recommendation:** When closing Finding 3.1, normalize the sequence in either §UC-3 or AC-7 (use the AC-7 form including `/reload-plugins` since it's stricter).

## 7. Self-Reported Confidence (per 5-dim reflection rubric — for blind calibration)

- citation_grounding: 4  (every numbered finding cites SPEC line, TASKLIST line, or disposition file ref; one [INFERRED] flag on git-default-branch behavior in Finding 5.2)
- coverage_completeness: 4  (surveyed all 16 FRs, all 9 NFRs, all 10 ACs against tasklist; surfaced 2 unverified ACs — AC-7, AC-9; did not exhaustively map every guard-row to test; did not run the test suite)
- deviation_classification_clarity: 4  (HIGH for AC-7 missing entirely and claude CLI install unresolved; MEDIUM for verification gaps with execution-time risk; LOW for ambiguity and cosmetic spec drift — applied consistently)
- risk_surface_coverage: 4  (probed environment, git version behavior, CI ordering, cross-phase artifact deps, validator output assumptions, path-safety regex edge cases; did not probe network/auth risks at the marketplace push step beyond what OQ-4 already documents)
- recommendation_actionability: 4  (every finding has a concrete fix with file/step/specific change; some recommendations propose alternatives — e.g., 5.5 — which an executor must choose between)
- self_reported_confidence: 0.82
- one_sentence_rationale: "Found two HIGH gaps the prior QA missed (AC-7 has no verifier; CI claude install command unresolved), four MEDIUM execution-time risks, and several LOW spec/disposition drifts — all evidence-cited and actionable, but I did not execute any tests or read every research file in full."

## 8. Inferred Claims Count

citations_total: 18
citations_inferred: 1
