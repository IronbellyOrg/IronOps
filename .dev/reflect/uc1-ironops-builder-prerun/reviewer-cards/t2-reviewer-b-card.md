# T2 Reviewer B Card — Completion+Operational Angle

**Status:** Complete
**Persona:** self-review (completion/operational)
**Model class:** opus-4.7-1m
**Date:** 2026-05-27

## 1. Findings — Items That Will Stall a Fresh Executor

### Finding 1.1 — Step 7.3 v0.1 manifest contradicts itself on skill count ("10 skill directory imports … 11 agents + 8 skill directories") [HIGH]

**Evidence:** Step 7.3 (TASKLIST L355) opens with "**all 10 skill directory imports**" and enumerates ten names (`sc-troubleshoot-protocol, sc-crash-recovery, sc-cli-portify-protocol, sc-cleanup-audit-protocol, sc-task-protocol, task, task-builder, tech-research, tdd, tech-reference`), but the SAME item earlier cites "research/01-file-inventory.md §6.5 + §7 (the v0.1 manifest content sketch with **11 agents + 8 skill directories + 7 commands**…)". The Key Objectives §8 (TASKLIST L80) says "10 skill directories — `~8` in spec §13 is approximate". Three numbers (8, 10, "approximate") in one item without a single canonical count. Grounded.

**Severity:** HIGH — A fresh executor reading L355 will not know whether to author an 8-skill or 10-skill manifest. AC-2 golden-output test (Step 6.4 L329) ALSO hardcodes "11 agents + 10 skills + 7 commands" while Step 6.4's preamble cites "~8 skills" from inventory §2.13 — so a 10-skill manifest will pass Step 6.4's count check but the executor may write 8 to "match the research" and have golden-fixture asserts fail in Step 9.2.

**Recommendation:** Replace every occurrence of "~8" / "8 skill directories" inside Step 7.3 with the literal "10" (with the same 10-name enumeration). Cross-update Step 6.4's inventory citation to point at the 10-skill count. Add a one-line note in Step 7.3 that the §13 spec figure "~8" is approximate and the literal count is 10.

### Finding 1.2 — Step 7.3 lists 7 command imports but `requires:` mapping for `git` and `workflow` is unspecified [MEDIUM]

**Evidence:** Step 7.3 (TASKLIST L355) enumerates 7 commands: `troubleshoot, git, cli-portify, cleanup-audit, task, research, workflow`. Five have explicit `requires:` (troubleshoot→sc-troubleshoot-protocol, cli-portify→sc-cli-portify-protocol, cleanup-audit→sc-cleanup-audit-protocol, task→sc-task-protocol, research→tech-research). The `git` and `workflow` commands have NO `requires:` field documented. If `git.md` or `workflow.md` in IronClaude upstream contain a `Skill sc:<x>-protocol` reference, the FR-4 co-import scan will fail the build with `CO_IMPORT_MISSING`. Grounded.

**Severity:** MEDIUM — Easy to verify but if missed, breaks first production build.

**Recommendation:** Pre-execution task-build step: `grep -l "Skill sc:" /config/workspace/IronClaude/src/superclaude/commands/{git,workflow}.md` — if either file matches, add the corresponding `requires:` clause to Step 7.3 manifest enumeration. Restructure Step 7.3 as an explicit table of (command, requires) pairs.

### Finding 1.3 — Step 4.13 snapshot bootstrap cannot serve Step 6.4 golden-output test [HIGH]

**Evidence:** Step 4.13 (TASKLIST L285) instructs copying "only the four documented files plus the LICENSE" — `devops-architect.md`, `system-architect.md`, `sc-troubleshoot-protocol/SKILL.md` (+refs/rules subdirs as present), `troubleshoot.md`. Step 6.4 (TASKLIST L329) `test_golden_output.py` "runs the builder against the ironclaude-snapshot fixture **and the v0.1 manifest**, walk the rendered staging tree". The v0.1 manifest (Step 7.3) imports 11 agents + 10 skill dirs + 7 commands. The hermetic snapshot has only 2 agents + 1 skill dir + 1 command. When Step 6.4's test runs against the v0.1 manifest, Stage 3 RENDER hits `commands/cleanup-audit.md`, finds no such file in the snapshot, and raises `UnresolvedImport` — NEVER reaching the golden-tree comparison. Grounded.

**Severity:** HIGH — Step 6.4 cannot satisfy AC-2 with the snapshot as specified.

**Recommendation:** Either (a) expand Step 4.13 to copy ALL files referenced by the v0.1 production manifest (28 imports → roughly 150 files when skill dirs expand) AND name them explicitly, OR (b) split into two fixtures: `tests/fixtures/ironclaude-snapshot/` (minimal 4-file for unit/conftest) and `tests/fixtures/ironclaude-full-snapshot/` (complete for golden test); update Step 6.4 to use the full snapshot. Pick (b) — it preserves unit-test hermeticity while enabling the AC-2 path.

### Finding 1.4 — Step 4.5 `mock_git_clone` cannot serve TWO different snapshots [MEDIUM]

**Evidence:** Step 4.5 (TASKLIST L253) `mock_git_clone` "replaces subprocess.run for git clone/ls-remote with a fake that copies from `ironclaude_snapshot_path`". The conftest binds this to ONE session-scoped path. If Finding 1.3 is resolved via approach (b), the conftest needs TWO fixture variants (minimal vs full). Step 6.1 integration `test_pipeline.py` uses `good_manifest` (minimal); Step 6.4 golden test would need the full snapshot. Grounded.

**Severity:** MEDIUM — Same root cause as 1.3; surfaces during integration.

**Recommendation:** When resolving 1.3, parametrize Step 4.5's `mock_git_clone(snapshot_path)` so tests pick the right snapshot, and ensure `ironclaude_snapshot_path` becomes a fixture-of-fixtures pattern (one minimal, one full).

### Finding 1.5 — Step 6.5 `cli build bad manifest` invocation lacks `--staging` and `--marketplace` — flag defaults unspecified [HIGH]

**Evidence:** Step 6.5 (TASKLIST L333) test calls `runner.invoke(cli, ["build", "--manifest", str(bad_manifest_path)])` — no `--staging` flag, no `--marketplace` flag, no `--dry-run`. Step 3.10 (TASKLIST L211) defines the `build` subcommand options as `--manifest, --staging, --marketplace, --dry-run, --verbose` but does NOT specify `required=` or `default=` for any of them. Three possibilities: (a) click defaults `required=False` and `default=None`, in which case `staging=None` is passed to `BuildContext` and downstream stages crash with `AttributeError: 'NoneType' object has no attribute '...'`; (b) executor adds `required=True` for `--staging` and `--marketplace`, in which case the test exits with click usage error (exit code 2), NOT the categorical NFR-7 code; (c) executor invents defaults like `--staging ./staging`. Grounded.

**Severity:** HIGH — Test 6.5 will produce confusing failures; executor will guess at defaults; defaults bleed into production behavior.

**Recommendation:** Step 3.10 must specify each option's `required` and `default` explicitly. Suggested: `--manifest` (required=True), `--staging` (default=`./staging`, type=click.Path), `--marketplace` (required when `--dry-run` is False, otherwise optional via callback validator), `--dry-run` (is_flag=True, default=False), `--verbose` (is_flag=True, default=False). Cross-reference Step 6.5 to use these defaults explicitly when invoking the CLI.

## 2. Findings — Hidden Assumptions

### Finding 2.1 — IronOps git repo must already be initialized at `/config/workspace/IronOps/` with ≥1 commit [HIGH]

**Evidence:** Step 3.6 (TASKLIST L195) `_resolve_builder_version()` runs `git -C <ironops-repo-root> rev-parse HEAD` and `git status --porcelain`. Step 1.1 (TASKLIST L151) starts execution without any "ensure git is initialized" preflight. If `/config/workspace/IronOps/` is not a git repo or has zero commits, `git rev-parse HEAD` returns non-zero (`fatal: ambiguous argument 'HEAD'`), Stage 0 PREFLIGHT (Step 3.9 L207) raises an unexpected error (not the documented `BUILDER_DIRTY_TREE` because that's specifically for dirty-tree). Step 7.9 (the first end-to-end smoke) will be the first venue this surfaces. Grounded.

**Severity:** HIGH — First end-to-end execution fails with opaque error.

**Recommendation:** Add a Step 1.0 (or amend Step 1.2): "Confirm `/config/workspace/IronOps/` is a git repository (`git -C /config/workspace/IronOps rev-parse --is-inside-work-tree` returns `true`) with at least one commit (`git -C /config/workspace/IronOps log -1 --format=%H` returns a SHA). If not, the executor must `git init` + initial commit before proceeding." Additionally Step 3.6 should raise a distinct categorical code (e.g., a new `BUILDER_NOT_A_GIT_REPO`) instead of generic Exception when HEAD is missing.

### Finding 2.2 — `claude` CLI version is never pinned (reproducibility + risk-row L551 unhonored) [HIGH]

**Evidence:** Step 7.2 (TASKLIST L351) installs the claude CLI with deferred "log a blocker if the exact npm package name has changed" — already flagged in T1 5.1. Deeper: even with the right install command, the SPEC risk-table row (SPEC L551) "claude plugin validate semantics change between Claude Code versions — Pin Claude Code version in CI" is not honored anywhere. No step pins `@anthropic-ai/claude-code@<version>` in workflows. Validator semantics drift → CI starts failing without code change. NFR-1 reproducibility is silently violated. Grounded.

**Severity:** HIGH — Reproducibility (NFR-1) silently broken; documented mitigation for row L551 absent.

**Recommendation:** Step 7.2 must pin a specific claude CLI version (verify current stable via `npm view @anthropic-ai/claude-code versions --json` at task-build time and pin that). Add a CHANGELOG entry (Step 7.7) noting "validator pinned to claude-code@X.Y.Z; bumping requires re-running the golden snapshot test".

### Finding 2.3 — Marketplace upstream URL uses SSH but CI has no SSH key [MEDIUM]

**Evidence:** Step 7.3 (TASKLIST L355) v0.1 manifest declares `ironclaude: url: "git@github.com:IronbellyOrg/IronClaude.git"` (SSH). Step 3.4 `sources.py` runs `git clone --depth=1 --branch <ref> <url> <dest>` literally with that URL. In CI (Step 7.2 `.github/workflows/build-publish.yml`), there is NO `webfactory/ssh-agent` or equivalent SSH-key setup — only `IRONOPS_MARKETPLACE_TOKEN` (a PAT, HTTPS auth). When Stage 1 CLONE runs `git clone git@github.com:...` on the CI runner, it fails with `Permission denied (publickey)`. Local dev with the user's SSH key masks the issue. Grounded.

**Severity:** MEDIUM — Production build dies at Stage 1 on first CI run.

**Recommendation:** Either (a) change manifest URL in Step 7.3 to `https://github.com/IronbellyOrg/IronClaude.git` and configure git in CI to use PAT via `git config --global url."https://x-access-token:${TOKEN}@github.com/".insteadOf "https://github.com/"`, OR (b) add an `webfactory/ssh-agent@v0.x` step + `secrets.IRONOPS_SSH_DEPLOY_KEY` to the workflow and document in `docs/MARKETPLACE_BOOTSTRAP.md`. Pick (a) for simplicity since the marketplace push already uses a PAT.

### Finding 2.4 — `make build` references `manifest.yaml` before Phase 7 creates it [LOW]

**Evidence:** Step 3.12 (TASKLIST L219) `make build` target runs `uv run ironops build --manifest manifest.yaml --staging dist/staging --dry-run`. `manifest.yaml` is created in Step 7.3 (TASKLIST L355). Anyone running `make build` between Phase 3 and Phase 7 sees `FileNotFoundError`. Step 3.15 QA gate runs `make lint`, not `make build`, so the failure won't surface during scaffolding QA, but it's a usability footgun. Grounded.

**Severity:** LOW — Cosmetic; affects developer experience.

**Recommendation:** Either (a) `make build` should have a guard `[ -f manifest.yaml ] || { echo "manifest.yaml required"; exit 1; }`, OR (b) defer adding the `build` target to a Phase 7 sub-step that updates the Makefile after the manifest exists.

### Finding 2.5 — `rsync` is a hidden system dependency not declared anywhere user-visible [MEDIUM]

**Evidence:** Step 3.8 (TASKLIST L203) `publish.py` invokes `rsync -a --delete`. Stage 0 PREFLIGHT (Step 3.9 L207) checks "`python3.11+`, `git`, `rsync` available" — but `pyproject.toml` (Step 3.11 L215) lists ONLY `click>=8.0` + `PyYAML>=6.0` as runtime deps. The README (Step 7.8) "Install" section says only `uv pip install -e .` — no mention of `apt install rsync` or `brew install rsync`. macOS ships rsync 2.6.9 (2006); `--delete` semantics differ from GNU rsync 3.x. Grounded.

**Severity:** MEDIUM — Minimal Docker base images won't have rsync; macOS users may hit version-skew issues.

**Recommendation:** Add a "System prerequisites" section to README (Step 7.8): "Required: `git >= 2.30`, `rsync >= 3.1.0`, `python >= 3.10`". Step 3.9 PREFLIGHT should `shutil.which("rsync")` AND validate version via `rsync --version` parsing, raising a documented error code.

## 3. Findings — Weak Definition-of-Done

### Finding 3.1 — Phase 3 QA gate (Step 3.15) does not verify modules actually import [HIGH]

**Evidence:** Step 3.15 (TASKLIST L231) runs `make dev` + `make lint`. Neither imports the 10 new modules. They could be ruff-clean but have import-time errors: missing symbols in `from ironops.errors import X`, circular imports, typos in cross-module references. Failures surface as pytest collection errors in Phase 5, making the failing module harder to pinpoint and breaking the per-module diagnosis pattern. Grounded.

**Severity:** HIGH — Phase 3 declared "done" while modules may not import.

**Recommendation:** Step 3.15 must add: `uv run python -c "import ironops, ironops.errors, ironops.manifest, ironops.sources, ironops.render, ironops.metadata, ironops.validate, ironops.publish, ironops.pipeline, ironops.cli; print('imports ok')"`. PASS verdict requires lint + dev install + imports all green.

### Finding 3.2 — Phase 7 QA gate (Step 7.9) skips silently if `claude` CLI absent [MEDIUM]

**Evidence:** Step 7.9 (TASKLIST L379) "skip with a documented note if `claude` CLI is not installed". AC-3 (SPEC L503) requires `claude plugin validate` passes. The local QA gate has no enforcement — AC-3 is then only verified in CI, but the CI workflow (Step 7.2) hasn't itself been validated to run. Grounded.

**Severity:** MEDIUM — Local QA may declare success while AC-3 is unverified.

**Recommendation:** Step 7.9 should FAIL the gate (not skip) when `claude` is absent, with a clear remediation message including the pinned-version install command from Finding 2.2's resolution.

### Finding 3.3 — Step 8.2 rf-qa prompt doesn't require ANY test summary to be PASS [HIGH]

**Evidence:** Step 8.2 (TASKLIST L389) tells rf-qa to verify "FR coverage, NFR coverage, AC verification". The prompt does NOT explicitly require that each of the four aggregated phase summaries (Step 8.1 inputs: phase3-lint, unit-pytest, integration-pytest, phase7-validate) be VERDICT=PASS. rf-qa could read a summary that says "FAIL: 3 unit tests failing, logged blocker" and still declare task-integrity PASS based on coverage matrix completeness. Grounded.

**Severity:** HIGH — The entire phase-gate mechanism is undermined.

**Recommendation:** Step 8.2's prompt must add: "ADVERSARIAL VERIFICATION: Each of the four phase summaries' explicit verdict line MUST be PASS. If ANY summary's verdict is FAIL or contains a logged blocker, rf-qa returns FAIL with the offending gate cited." Step 9.4 (mark Done) must add precondition: "no phase summary may contain `verdict: FAIL`; otherwise set `status: Blocked`."

### Finding 3.4 — "log a blocker, then mark this item complete" escape hatch in EVERY item poisons every gate [HIGH]

**Evidence:** Every checklist item ends with: "If unable to complete due to [reason], log the specific blocker … then mark this item complete." All 65+ items, including the four phase-QA gates (Steps 3.15, 5.6, 6.7, 7.9) and the post-completion gates (Steps 9.1, 9.2). A literal-minded executor following the letter of the instructions can mark every item complete with logged blockers and reach Step 9.4 with status=Done despite zero passing tests. Grounded.

**Severity:** HIGH — Systemic; the entire MDTM contract becomes a no-op.

**Recommendation:** Add a header note in `## Detailed Task Instructions` (before Phase 1): "The 'log blocker, mark complete' clause applies only to non-gate items. The following items are LOAD-BEARING — for these, logging a blocker means HALT execution with status=Blocked, DO NOT mark complete: Steps 3.15, 5.6, 6.7, 7.9, 8.3, 9.1, 9.2." Replace the boilerplate tail on those specific items accordingly.

## 4. Findings — AC Fidelity Gaps

### Finding 4.1 — AC-1 ("Builder runs to green on CI") has no step that proves CI actually ran [HIGH]

**Evidence:** AC-1 (SPEC L501) requires "GitHub Actions log shows exit 0". Step 9.2 (TASKLIST L403) runs validations LOCALLY (`uv run pytest`, `make lint`, `ruff format --check`). No step pushes a branch, triggers a workflow_dispatch, waits for the run, and records exit_code. The `.github/workflows/*.yml` files are created but never invoked. Grounded.

**Severity:** HIGH — AC-1's verification clause demands a green CI log; task produces workflow files but doesn't prove they work.

**Recommendation:** Add Step 9.5: "Push the implementation branch to `origin`; run `gh workflow run test.yml --ref <branch>` and `gh run list --workflow=test.yml --limit=1 --json conclusion`; assert `conclusion == 'success'`; record run URL in `phase-outputs/reports/ac1-ci-evidence.md`. AC-1 PASS only when CI run conclusion is success." Acceptable fallback: `act` for local GitHub Actions execution.

### Finding 4.2 — AC-4 ("META.json lists every emitted file with non-empty resolved_sha") softened to "spot-check 3" [MEDIUM]

**Evidence:** Step 5.5 test_metadata (TASKLIST L307) "spot-check 3 file SHAs" per AC-4 verification clause, but SPEC AC-4 (L504) says "lists every emitted file with a non-empty `resolved_sha`". 3 of ~150 files is 2% coverage, not "every". Grounded.

**Severity:** MEDIUM — SPEC verification clause itself says "spot-check 3" so the tasklist is following the SPEC literal. The mismatch is inside the SPEC.

**Recommendation:** Either amend SPEC AC-4 to say "spot-check 3 file SHAs PLUS asserting len(meta.sources[].imports) == M (where M is the actual emitted file count)" OR strengthen Step 5.5 to assert all emitted files have a SHA without amending SPEC. Pick the latter — defensive coverage with no spec change.

### Finding 4.3 — AC-6 ("Marketplace receives one new commit per build") vs no-changes skip path [MEDIUM]

**Evidence:** AC-6 (SPEC L506) "Marketplace repo receives one new commit per build". Step 3.8 (TASKLIST L203) `_commit_and_push` "to detect no-changes (skip commit + push when empty per B.8 step 2 — return PublishResult(pushed=False, commit_sha=None, ...))". A deterministic re-run with no upstream commits returns `pushed=False` — NO commit. This VIOLATES AC-6's "one new commit per build" literal. Grounded.

**Severity:** MEDIUM — AC-6 is either loosely-worded or the implementation is wrong.

**Recommendation:** Amend SPEC §AC-6 in Phase 2 to "Marketplace repo receives one new commit per build that emits content changes; no-op rebuilds skip commit and exit 0 with `pushed: false`". Document the skip path explicitly in `docs/MARKETPLACE_BOOTSTRAP.md`.

### Finding 4.4 — AC-7 install-and-invoke smoke (T1 3.1) — independently confirmed missing [HIGH]

**Evidence:** Grepped TASKLIST for `AC-7`, `claude plugin install ironops-devops@`, `/reload-plugins`, `smoke test`, `install-and-invoke`: zero hits anywhere outside the `related_docs` block. Confirms T1 3.1. Grounded.

**Severity:** HIGH.

**Recommendation:** T1's recommendation stands — add `tests/integration/test_smoke_install.py` gated behind `RUN_SMOKE=1` env var, OR a manual checklist signoff under `phase-outputs/reviews/ac7-smoke-signoff.md` referenced as a Phase 9 item.

### Finding 4.5 — AC-8 ("All 16 FR-N have CI test or assertion") matrix can pass with FR gaps [MEDIUM]

**Evidence:** Step 6.6 (TASKLIST L337) creates `tests/test_inventory.md` listing FRs+NFRs+ACs in a matrix. Step 6.6 does not specify rejecting FRs whose "Test File" column is empty. If FR-13 (plugin.json omits version) has no explicit test, the matrix has an empty row and AC-8 still appears satisfied (the file exists). Grounded.

**Severity:** MEDIUM.

**Recommendation:** Step 6.6 must add: "After populating the table, scan for FR-1..FR-16 rows with empty 'Test File' column. If any FR has no test reference, halt with blocker." Step 8.2 rf-qa prompt should re-verify this.

### Finding 4.6 — AC-9 Guard Boundary coverage report (T1 3.2) — independently confirmed missing [MEDIUM]

**Evidence:** Grepped for `guard-boundary-coverage`, `guard.boundary`, `§9 rows`: zero. Step 6.6 mentions guard-boundary rows in passing but produces no separate coverage artifact. AC-9 verification "Coverage report in build artifacts" is unsatisfied. Confirms T1 3.2. Grounded.

**Severity:** MEDIUM.

## 5. Findings — Test Fixture Realism

### Finding 5.1 — `tests/fixtures/ironclaude-snapshot/` content underspecified for AC-2 [HIGH]

**Evidence:** Step 4.13 (TASKLIST L285) prescribes "the four documented files plus the LICENSE" — `devops-architect.md`, `system-architect.md`, `sc-troubleshoot-protocol/SKILL.md` (+ "refs/rules subdirs as present"), `troubleshoot.md`. I verified `/config/workspace/IronClaude/src/superclaude/skills/sc-troubleshoot-protocol/` has `SKILL.md` (40,457 bytes) and `refs/` — NO `rules/` subdir. Step 4.13's "refs/rules subdirs as present" is ambiguous: "as present" could mean "those that exist" (so only refs/) or "copy refs/ AND rules/" (the latter is a no-op since rules/ doesn't exist). Worse, Step 6.4 golden test asserts skill_count=10 against the v0.1 manifest. Grounded — verified via `ls` of the live source.

**Severity:** HIGH — Same root cause as Finding 1.3.

**Recommendation:** Step 4.13 must explicitly enumerate ALL files needed by the FULL v0.1 manifest (28 imports → ~150 files when skills expand). Verify each enumerated file exists at task-build time via:
- 11 agent files: `{devops-architect, system-architect, security-engineer, root-cause-analyst, performance-engineer, backend-architect, quality-engineer, pm-agent, self-review, technical-writer, requirements-analyst}.md`
- 7 command files: `{troubleshoot, git, cli-portify, cleanup-audit, task, research, workflow}.md`
- 10 skill directories: `{sc-troubleshoot-protocol, sc-crash-recovery, sc-cli-portify-protocol, sc-cleanup-audit-protocol, sc-task-protocol, task, task-builder, tech-research, tdd, tech-reference}/` — each with `SKILL.md` plus whatever `refs/`/`rules/`/`templates/`/`scripts/` exist
- LICENSE

Use `cp -r` on entire skill dirs rather than file-by-file selection (Finding 5.2 dependency).

### Finding 5.2 — Step 4.13 fails to copy support files referenced inside skill `SKILL.md` [MEDIUM]

**Evidence:** Skill SKILL.md files often instruct agents to `Read refs/00-foo.md` or `Read templates/bar.md`. Step 4.13's "refs/rules subdirs as present" is ambiguous and the snapshot may end up containing `SKILL.md` without its referenced support files. FR-8 path-safety check (Step 3.5) only validates path strings are inside plugin root — it does NOT verify referenced files exist. Result: build succeeds, plugin ships, runtime references fail. Grounded.

**Severity:** MEDIUM — Latent v0.1 plugin defect; not caught at build time.

**Recommendation:** Step 4.13 must `cp -r` entire skill directories per skill. Optionally add a render.py check that emits warnings for `Read <relative-path>` references whose targets aren't in the emitted file set (post-render lint pass). This complements the existing FR-8 path-safety scan.

### Finding 5.3 — Hermetic `ironclaude_fixture_repo` `git init` default-branch is unstable (confirms T1 5.2) [MEDIUM]

**Evidence:** Step 4.5 conftest `ironclaude_fixture_repo` runs `git init` + commit. Git's default-branch behavior varies by version: `master` on git < 2.28, `main` on git ≥ 2.28 with `init.defaultBranch=main`, follow-the-config otherwise. `_resolve_default_branch` via `git ls-remote --symref` will parse whatever the repo declares. CI runners may have different git versions than the dev environment. Confirms T1 5.2 from a different angle. Grounded.

**Severity:** MEDIUM.

**Recommendation:** Step 4.5 conftest's `ironclaude_fixture_repo` must explicitly:
1. Run `git init --initial-branch=main` (git ≥ 2.28) OR `git init && git symbolic-ref HEAD refs/heads/main` (compat for older git).
2. Set `git config user.email test@example.invalid && git config user.name test`.
3. Commit with `--no-gpg-sign` to avoid keyring failures in CI.

## 6. Findings — CI Workflow Concrete-ness

### Finding 6.1 — Step 7.2 marketplace checkout step has no literal YAML [HIGH]

**Evidence:** Step 7.2 (TASKLIST L351) prose: "checkout marketplace repo at `IronbellyOrg/ironops-marketplace` into `marketplace-clone/` using `secrets.IRONOPS_MARKETPLACE_TOKEN`". This requires precise `actions/checkout@v4` syntax: `repository:`, `token:`, `path:`, and likely `fetch-depth: 0` (to enable `git push origin <branch>` without a shallow-clone limitation). Prose-only spec leaves multiple ways to get it wrong. Empty marketplace repo (per OQ-3 bootstrap) may fail checkout with "could not read Username". Grounded.

**Severity:** HIGH — First production CI run won't work.

**Recommendation:** Step 7.2 must specify the literal YAML block:
```yaml
- uses: actions/checkout@v4
  with:
    repository: IronbellyOrg/ironops-marketplace
    token: ${{ secrets.IRONOPS_MARKETPLACE_TOKEN }}
    path: marketplace-clone
    fetch-depth: 0
```
Document in `docs/MARKETPLACE_BOOTSTRAP.md` (Step 7.6) that the marketplace repo MUST have at least one commit on its default branch before the workflow runs (initial bootstrap commit per OQ-3).

### Finding 6.2 — Step 7.2 `on-failure use actions/upload-artifact@v4` syntax doesn't exist [MEDIUM]

**Evidence:** Step 7.2 (L351) prose: "on-failure use `actions/upload-artifact@v4` to upload `staging/validate.log` and `staging/build.log`". GitHub Actions has NO `on-failure:` directive; the correct pattern is `if: failure()` on the step. Grounded.

**Severity:** MEDIUM — Confusing wording; common pitfall.

**Recommendation:** Step 7.2 must specify literal YAML:
```yaml
- name: Upload build artifacts on failure
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: build-logs
    path: |
      staging/validate.log
      staging/build.log
    retention-days: 30
```

### Finding 6.3 — Step 7.1 `uv pip install --system` may fail PEP 668 on ubuntu-latest [MEDIUM]

**Evidence:** Step 7.1 (TASKLIST L347) "`uv pip install --system -e ".[dev]"`". Ubuntu since 2023 enforces PEP 668 ("externally-managed-environment") for system pip. UV's `--system` flag bypasses some restrictions but its semantics may not be what the executor expects on current `ubuntu-latest`. Grounded — INFERRED on exact UV+ubuntu interaction for current UV versions.

**Severity:** MEDIUM — May or may not work; if it fails, fix is one-line.

**Recommendation:** Step 7.1 should use the canonical UV CI pattern from https://docs.astral.sh/uv/guides/integration/github/: `astral-sh/setup-uv@v3` action, then `uv sync --all-extras` or `uv venv && source .venv/bin/activate && uv pip install -e ".[dev]"`. Reference the docs URL in the step description.

### Finding 6.4 — Neither workflow caches `~/.cache/uv` — repeated dep downloads consume NFR-2 budget [LOW]

**Evidence:** Steps 7.1 and 7.2 lack `actions/cache@v4` for UV cache. Cold dep install costs ~30s per matrix cell. NFR-2 60s soft budget halved by cold install. Grounded.

**Severity:** LOW — Performance only.

**Recommendation:** Add to both workflows:
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/uv
    key: uv-${{ runner.os }}-${{ hashFiles('pyproject.toml') }}
```

### Finding 6.5 — Step 7.2 schedule cron at 06:00 UTC competes with concurrency: ironops-publish [LOW]

**Evidence:** Step 7.2 declares both `schedule: - cron: '0 6 * * *'` AND `concurrency: group: ironops-publish`. If a push-triggered run is in flight at 06:00 UTC, the scheduled run is queued; if the push run takes >5min, queue may pile up. With single-instance concurrency, scheduled runs from prior days may stack. Grounded.

**Severity:** LOW — Edge case.

**Recommendation:** Add `concurrency.cancel-in-progress: true` to drop stale queued runs (acceptable since the new build supersedes them), OR document this behavior in `docs/MARKETPLACE_BOOTSTRAP.md`.

## 7. Confirmations Against T1

I independently confirm:

- **T1 3.1 (AC-7 install-and-invoke missing)** — Confirmed via grep. My Finding 4.4.
- **T1 3.2 (AC-9 Guard Boundary coverage report missing)** — Confirmed. My Finding 4.6.
- **T1 3.3 (NFR-2 timing never measured)** — Confirmed. Step 3.9 mentions instrumentation but no test asserts; categorical exit code for timing-overrun is undocumented.
- **T1 3.4 (NFR-8 no regression test)** — Confirmed.
- **T1 4.1 (Step 3.10/3.11 entry-point `cli:main` vs D2 `cli:cli`)** — Confirmed. D2 literal is `"ironops.cli:cli"`; tasklist silently uses `cli:main`.
- **T1 4.3 (Step 3.7 NFR-4 strict-warnings underspec)** — Confirmed.
- **T1 4.4 (Step 4.5 `mock_claude_validate` API unspecified)** — Confirmed; extended in my Finding 1.4 (same problem for `mock_git_clone`).
- **T1 5.1 (Step 7.2 claude CLI install unresolved)** — Confirmed; deepened in my Finding 2.2 (no version pin).
- **T1 5.2 (default-branch behavior in `ironclaude_fixture_repo`)** — Confirmed in my Finding 5.3.
- **T1 5.5 (REGEN_GOLDEN chicken-and-egg)** — Confirmed; amplified by my Findings 1.3/5.1 (snapshot lacks files to regen).
- **T1 6.1 (§13 "~8 skills" vs Step 7.3 "10 skills")** — Confirmed; my Finding 1.1 elevates severity because Step 7.3 contradicts itself within one item.

## 8. Disagreements With T1

- **T1 3.5 (Spec §17 wording underspec, LOW)** — Suggest bumping to MEDIUM: Step 8.1's "two spec amendment locations quoted exactly" check tolerates text variance, which propagates ambiguity into the QA evidence chain.
- **T1 5.6 (Step 3.6 `_resolve_builder_version` repo path, LOW/MEDIUM)** — I rate HIGH (my Finding 2.1). T1 covers the CI runner path-resolution case; the more pressing issue is the IronOps repo not being initialized as a git repo at the start of execution.
- **T1 overall confidence (0.82)** — Slightly lower (0.78) is warranted because T1 missed: (a) snapshot file count vs v0.1 manifest mismatch (my 1.3, 5.1); (b) SSH URL in manifest vs PAT-only CI auth (my 2.3); (c) workflow YAML imprecision in checkout/upload-artifact (my 6.1, 6.2); (d) systemic "log blocker mark complete" escape hatch (my 3.4); (e) `make build` referencing manifest.yaml before Phase 7 (my 2.4); (f) rsync as undeclared system dep (my 2.5); (g) module-import smoke missing from Phase 3 QA gate (my 3.1). These are operational/will-this-actually-build issues a structural review would naturally miss.
- **No outright disagreement with T1's specific findings** — T1's findings are well-grounded; my disagreement is on severity grading and coverage breadth, not on factual claims.

## 9. Self-Reported Confidence

- citation_grounding: 4  (every finding cites SPEC/TASKLIST line or disposition; verified IronClaude snapshot dir contents on disk for 5.1; one INFERRED on UV+PEP 668 specifics in 6.3)
- coverage_completeness: 4  (probed every Phase QA gate, every AC, snapshot fixture against real disk, CI workflow YAML correctness, env/auth assumptions; did not enumerate all 26 guard-boundary rows beyond confirming T1)
- deviation_classification_clarity: 4  (HIGH reserved for executor-stall + missing CI verification + systemic completion escape hatch; MEDIUM for spec-vs-implementation drift with execution risk; LOW for ergonomic/cosmetic)
- risk_surface_coverage: 5  (covered fixture realism vs production manifest, SSH vs PAT auth, hidden system deps like rsync, IronOps repo initialization, version pinning for reproducibility, YAML syntax correctness in workflows, multi-snapshot conftest conflict — all gaps T1 missed)
- recommendation_actionability: 5  (every recommendation specifies a concrete change with literal YAML blocks, literal flag defaults, literal directory enumerations; alternatives clearly labeled a/b)
- self_reported_confidence: 0.85
- rationale: "Operational angle caught 7 issues T1's structural pass missed (snapshot realism, SSH auth, two workflow YAML imprecisions, repo-not-init preflight, completion escape hatch, module-import smoke, rsync sys-dep); confirmed all T1 HIGH/MEDIUM findings; verified snapshot file inventory against live disk state; did not execute the tasklist against fresh disk so a small number of executable-only issues may remain."
