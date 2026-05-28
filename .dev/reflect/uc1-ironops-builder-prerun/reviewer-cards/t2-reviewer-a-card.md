# T2 Reviewer A Card — Structural+Regression Angle

**Status:** Complete
**Persona:** rf-qa (adversarial structural)
**Model class:** Opus 4.7 (1M context)
**Date:** 2026-05-27

Independently audited the IronOps v0.1 task file from a STRUCTURAL+REGRESSION-RISK perspective. Read SPEC, full TASKLIST (Phases 1–9), disposition, T1 card. Adversarial stance: assume subtle errors remain after T1's first pass.

---

## 1. Findings — Spec Ambiguities Silently Resolved

### Finding 1.1 — §10 N=26 manifest count vs Step 7.3 actual N=28 imports [MEDIUM] [Grounded]

**Evidence:** SPEC §10 L435 declares the manifest fanout assumption `N=26 → M≈150` and SPEC §13 L520-524 lists "Agents (11), Skills (~8), Commands (~7)" = 26. Step 7.3 (TASKLIST L355) instructs the manifest to list **11 agents + 10 skill directories + 7 commands = 28 imports** (skills expanded to 10 to satisfy FR-4 co-import for `sc-cleanup-audit-protocol` and `sc-task-protocol`). The disposition (D9 and prior QA) authorized the count expansion, but no item updates §10's `N=26` annotation OR §13's "Skills (~8)" wording in the spec itself. The §10 ANNOTATION inside `META.json.sources[*].imports[]` MUST enumerate every emitted file under that import (SPEC §10 L477) — but META.json's `summary.total_files: 26` schema example at SPEC §6 L329 is now stale because the v0.1 plugin emits ≥28 manifest entries fanning out to ~150 files.

**What task did:** Silently treated `~8` as approximate and let the manifest grow to 10, but did NOT amend §10 or §13 wording the way it amended §NFR-7 (D3) and §2.1+§17 (D4).

**Severity:** MEDIUM — AC-9 guard-coverage and AC-8 traceability cross-reference §10's stated counts. AC-4's META.json schema validation (against §6 L327-331 with `total_files: 26`) will FAIL on the v0.1 build because actual `total_files` ≈ 150 not 26 (the §6 example value), AND `agent_count: 11, skill_count: 8` example is contradicted (skill_count will be 10).

**Recommendation:** Add a Phase 2 Step 2.3 amending SPEC §10 L435 to `N=28` (or replace with `N` placeholder), SPEC §13 L520 "Skills (~8)" → "Skills (10)" enumerating the 10 with rationale, and clarify SPEC §6 L327 example values are illustrative (or update them to the actual v0.1 expected counts). Without this, AC-8 traceability cannot honestly map "every FR has a CI test" if the spec itself contradicts the manifest.

### Finding 1.2 — Step 7.3 hidden auth-context switch: `git@` SSH URL but CI uses HTTPS token [MEDIUM] [Grounded]

**Evidence:** Step 7.3 (TASKLIST L355) specifies the manifest's `sources.ironclaude.url: "git@github.com:IronbellyOrg/IronClaude.git"` (SSH form). Step 7.2 (TASKLIST L351) provisions `IRONOPS_MARKETPLACE_TOKEN` PAT secret for **HTTPS** clones (`secrets.IRONOPS_MARKETPLACE_TOKEN`) — but the manifest URL is SSH, requiring an SSH key not a PAT. GitHub Actions does not provide SSH agent by default; the workflow file does not call `webfactory/ssh-agent` or equivalent. This will cause `git ls-remote --symref git@github.com:...` to fail with `Permission denied (publickey)` at Stage 1.

**What task did:** Silently chose SSH URL form (matching SPEC §5 L263 example) while wiring an HTTPS-PAT auth flow in CI.

**Severity:** MEDIUM — Production build-publish workflow will fail at Stage 1 CLONE on its first run. T1 didn't catch this; it focused on `claude` CLI install (Finding 5.1) but missed the upstream-clone auth path.

**Recommendation:** Either (a) change manifest URL to HTTPS (`https://github.com/IronbellyOrg/IronClaude.git`) and use `extraHeader` with the PAT for `git config`, OR (b) add an `webfactory/ssh-agent@v0.9.0` step in Step 7.2 wired to an `IRONCLAUDE_DEPLOY_KEY` secret. Decide before merge; current state guarantees CI failure.

### Finding 1.3 — `_resolve_default_branch` parses `git ls-remote --symref` but FR-2-A3 says `git remote show` [LOW] [Grounded]

**Evidence:** SPEC FR-2-A3 (L102-103) reads: "Builder MUST resolve the upstream's default branch programmatically (`git remote show` or equivalent)." Step 3.4 (TASKLIST L187) chose `git ls-remote --symref` form (a DIFFERENT subprocess shape than `git remote show origin`). The deviation is documented inline in Step 3.4 ("NOTE: this deviates from research/04 §B.3..."). FR-2-A3's "or equivalent" allowance covers it, but the spec's verbatim recommendation is `git remote show`.

**What task did:** Picked the URL-based form (`ls-remote --symref`) because it eliminates a chicken-and-egg with the clone, then documented the deviation inline (good practice).

**Severity:** LOW — Acknowledged and reasoned; FR-2-A3's "or equivalent" explicitly permits this. But the spec's example text remains the literal authority and is silently overridden.

**Recommendation:** Either accept as-is (deviation is documented in tasklist), or add a one-line note to SPEC §FR-2-A3 explicitly listing `git ls-remote --symref <url> HEAD` as the recommended form (avoids a future audit treating the inline tasklist note as the canonical source instead of the spec).

---

## 2. Findings — Untested Invariants (§9 Guard Boundary Coverage)

**Coverage count vs §9's 26 rows:** Mapped each §9 row (SPEC L399-426) against existing Phase 5/6 test items.

### Finding 2.1 — Guard rows partially covered; AC-9 artifact missing [HIGH] [Grounded]

**Per-row mapping (`schema_version == "1"` family covered by Step 5.2 parametrize; `imports non-empty` partially covered; etc.):**

| §9 Row | Guard | Test Coverage | Status |
|---|---|---|---|
| 1 schema_version Zero/Empty | FR-14 | Step 5.2 (missing variant) | COVERED |
| 2 schema_version One/Minimal | FR-14 | Step 5.2 good.yaml | COVERED |
| 3 schema_version Typical | FR-14 | Step 5.2 good.yaml | COVERED |
| 4 schema_version Maximum/Overflow `"999"` | FR-14 | Step 5.2 + bad-schema fixture | COVERED |
| 5 schema_version Sentinel `"1.0"`, `"1.x"` | FR-14 | Step 5.2 parametrize | COVERED |
| 6 schema_version Legitimate Edge `1` (int) | FR-14 | Step 5.2 parametrize over `[..., 1]` | COVERED |
| 7 imports non-empty Zero/Empty | FR-15 | Step 5.2 + bad-empty-imports fixture | COVERED |
| 8 imports non-empty One/Minimal | FR-15 | Step 5.2 happy path | COVERED |
| 9 imports non-empty Typical (~26) | FR-15 | golden-output / test_pipeline | COVERED |
| 10 imports non-empty Max 10000 entries | FR-15 | **NONE** — no fixture, no warning-assertion test | **GAP** |
| 11 imports non-empty Sentinel Match (n/a) | — | n/a | n/a |
| 12 import.to not self-overwrite `.claude-plugin/plugin.json` | FR-16 | Step 5.2 + bad-self-overwrite | COVERED |
| 13 import.to not self-overwrite `META.json` | FR-16 | Step 5.2 parametrize | COVERED |
| 14 import.to not self-overwrite typical | FR-16 | Step 5.2 good.yaml | COVERED |
| 15 co-import orphan command | FR-4 | Step 5.4 + bad-orphan-command + Step 6.3 | COVERED |
| 16 co-import satisfied Typical | FR-4 | Step 5.4 happy | COVERED |
| 17 co-import skill without command (warn-not-fail) | FR-4 | Step 5.4 documented test | COVERED |
| 18 path Sentinel `../../etc/passwd` | FR-8 | Step 5.4 + bad-path-escape | COVERED |
| 19 path Typical `./scripts/x.sh` | FR-8 | Step 5.4 happy | COVERED |
| 20 path `${CLAUDE_PLUGIN_ROOT}/scripts/x.sh` | FR-8 | Step 5.4 documented test | COVERED |
| 21 validator_exit_code Zero/Empty (n/a) | — | n/a | n/a |
| 22 validator_exit_code Typical (0) | FR-5 | Step 6.1 happy | COVERED |
| 23 validator_exit_code Max (1..255) | FR-5 | Step 6.3 only exit 1; **no tests for 2..255 or timeout 124** | PARTIAL |
| 24 upstream clone Zero (timeout/auth fail) | FR-2 | Step 5.3 monkeypatch | COVERED |
| 25 upstream clone Typical | FR-2 | test_pipeline | COVERED |
| 26 IronOps dirty tree | FR-12 | Step 5.5 + Step 6.3 | COVERED |

**Coverage:** 22 of 24 substantive rows fully covered (rows 11, 21 are n/a). **Gaps:** Row 10 (10,000-entry stress + NFR-3 warning) and Row 23 partial (only exit code 1 exercised). AC-9 (SPEC L509) demands a **coverage report artifact** — T1's Finding 3.2 raised this but didn't enumerate the row-by-row gaps.

**Severity:** HIGH — AC-9 literal text requires ALL guard rows exercised. Row 10 also gates NFR-3 context-budget warning behavior, which currently has no test.

**Recommendation:** Add (a) a unit test in Step 5.2 with a synthetic 10,000-entry manifest asserting it loads AND emits a context-budget warning to stderr; (b) extend Step 6.3 to parametrize at least 3 distinct validator non-zero exit codes (1, 2, 124-timeout) all mapping to `VALIDATE_FAILED`; (c) require a new step to emit `phase-outputs/reports/guard-boundary-coverage.md` mapping every §9 row → test function name AND register as CI artifact in Step 7.1's upload-artifact.

---

## 3. Findings — Pipeline Flow Divergence Verification (§10)

### Finding 3.1 — N→M fanout is implemented but NOT asserted as a META.json invariant [MEDIUM] [Grounded]

**Evidence:** SPEC §10 L475-479 explicitly calls out the divergence point: "N=26 manifest → M=~150 emitted... META.json must enumerate every emitted file ... Downstream consumers of META.json should NOT assume `len(sources[*].imports) == len(manifest.imports)`". This is THE central pipeline correctness invariant.

Step 3.5 (TASKLIST L191) says directory imports expand via Glob and the fanout list is returned. Step 3.6 (L195) says META.json includes per-file `sources[].imports[]` fanout (FR-6-A1). Step 5.5 asserts `meta_json sources/imports enumerates every file`. Step 6.4 asserts `golden_file_count matches summary total_files`.

**What is NOT asserted:** No test in Phase 5/6 asserts the INEQUALITY `len(meta.sources[*].imports) > len(manifest.imports)` for v0.1 — i.e., that the fanout actually FANS OUT. A test passing when both equal `28` (no fanout) would silently regress. Also no unit test on a manifest with 1 directory import asserting >1 RenderedFile is produced.

**Severity:** MEDIUM — Fanout assertion is implicit in golden count match (Step 6.4) but brittle: regenerating the golden after dropping a skill subdirectory could regress fanout without detection.

**Recommendation:** Add `test_directory_import_fanout_strictly_exceeds_manifest_entries()` in Step 5.4: construct a manifest with 1 directory import containing 3 files, assert `len(rendered_files) == 3`. Add a test in Step 5.5 or 6.1: `sum(len(s.imports) for s in meta.sources) > len(manifest.imports)` for the v0.1 production manifest.

### Finding 3.2 — Stage 1/Stage 2 ordering: spec says "Stage 1 CLONE, Stage 2 READ MANIFEST" but Step 3.9 implements READ-then-CLONE in Stage 1 [MEDIUM] [Grounded]

**Evidence:** SPEC §7 L342-356 specifies Stage 1 = CLONE, Stage 2 = READ MANIFEST. CLONE iterates `sources[*]` which requires the manifest already parsed. Step 3.9 (L207) resolves by saying: "manifest.load_manifest is invoked at the START of Stage 1... Stage 2 READ MANIFEST (no-op re-validation pass... exists for spec-traceability)".

**Problem:** A "no-op re-validation" Stage 2 is a smell. If it re-runs the same validators, it's redundancy; if it doesn't, Stage 2 doesn't actually exist and the spec is lying. The spec's §7 stage numbering presumes a load-after-clone flow that is structurally impossible. This is a spec defect that the task papers over inside an item body instead of resolving with an amendment.

**Severity:** MEDIUM — Future audits comparing spec §7 against pipeline.py will flag a "missing" Stage 2. AC-8 mapping will hit ambiguity.

**Recommendation:** Add a Phase 2 spec amendment renumbering: `Stage 1 = READ MANIFEST`, `Stage 2 = CLONE`. Or amend §7 with: "Stage 1 implies a preceding manifest parse — implementations may merge the manifest parse into Stage 1's preamble".

### Finding 3.3 — `marketplace.json` lives OUTSIDE plugin root but §10 fanout doesn't acknowledge it [LOW] [Grounded]

**Evidence:** Step 3.6 sets `MARKETPLACE_JSON_PATH=".claude-plugin/marketplace.json"`. SPEC §7 Stage 4 L366 says "emit ../.claude-plugin/marketplace.json (FR-10)" — `../` indicates marketplace-repo root, NOT plugin root. SPEC §10 L459-461 correctly notes "+1 file at parent (marketplace.json)". Step 6.1 test_pipeline (L317) asserts "all four generated files exist post-build" — conflating plugin-root files (plugin.json, META.json, THIRD_PARTY_LICENSES.md) with marketplace-root file (marketplace.json).

**Severity:** LOW — Discovered during test implementation, but ambiguous wording could lead an executor to put all four in the plugin root, breaking FR-10's placement contract.

**Recommendation:** Update Step 6.1 to specify two separate existence assertions: three files at staging-dir, one at marketplace-repo. Same fix for golden tests and AC-2.

---

## 4. Findings — Phase-Ordering Subtleties

### Finding 4.1 — Step 6.4 golden test depends on manifest.yaml from Step 7.3 — local-bootstrap path broken at Step 9.2 [HIGH] [Grounded]

**Evidence:** Phase 6 runs BEFORE Phase 7. Step 6.4 (L329) `test_golden_output.py` depends on `/config/workspace/IronOps/manifest.yaml` (created in Step 7.3). The mitigation noted in Step 6.4 (`pytest.skip(...)` guard) was prior remediation #3, but the SKIP only handles the Phase 6 QA gate (Step 6.7). When Step 9.2 (final validation) runs `uv run pytest -v` (full suite), manifest.yaml exists but the golden JSON does NOT, so the test ACTIVATES and FAILS.

The bootstrap path is:
1. Step 6.4 creates test (skipped, no manifest)
2. Step 7.3 creates manifest
3. Step 9.2 runs full pytest — golden test now active but golden JSON missing — FAILS unless executor knows to run `REGEN_GOLDEN=1 uv run pytest tests/integration/test_golden_output.py` first.

T1's Finding 5.5 partially raised this for CI; the LOCAL execution sequence also breaks at Step 9.2.

**Severity:** HIGH — Step 9.2 will FAIL on first run because nothing in the chain bootstraps the golden JSON.

**Recommendation:** Insert a new Step 7.9.5 (or extend Step 9.2) explicitly: "If `tests/fixtures/golden/v0_1_plugin_tree.json` does not exist on disk, run `REGEN_GOLDEN=1 uv run pytest tests/integration/test_golden_output.py -v` to bootstrap the golden fixture, then COMMIT the JSON file before re-running the full suite."

### Finding 4.2 — `tests/test_inventory.md` (Step 6.6) cross-references test FUNCTION names but Phase 5 items don't pin names [MEDIUM] [Grounded]

**Evidence:** Step 6.6 (L337) requires the inventory to "cross-reference actual test function names". Steps 5.2/5.3/5.4/5.5 specify test COUNTS and SCOPES (13 tests, 8 tests, 11 tests, 13 tests) without pinning function names. Two executors will produce divergent names, breaking traceability.

**Severity:** MEDIUM — AC-8 verification becomes brittle.

**Recommendation:** Either (a) Steps 5.2/5.3/5.4/5.5 enumerate exact required test function names, OR (b) Step 6.6 describes the inventory in terms of `test_module::scope` not function name.

### Finding 4.3 — Source-file ordering: 3.1-3.10 create cross-importing modules BEFORE 3.11 creates pyproject.toml [LOW] [Grounded]

**Evidence:** Step 3.1 creates `__init__.py` with `__version__` matching pyproject.toml. Step 3.11 (L215) creates pyproject.toml. Step 3.15 (L231) runs `make dev` then `make lint`. Steps 3.1-3.10 create Python source files with cross-imports (`from ironops.errors import ...`) — between 3.1 and 3.11 the package isn't installable.

**Severity:** LOW — No item tests modules in isolation between 3.1-3.10, so this doesn't fail the task. Flag for awareness.

**Recommendation:** Optionally reorder pyproject.toml first; OR add a one-line note to Step 3.11 acknowledging it's the first step that makes earlier modules importable.

---

## 5. Findings — FR-9 Atomicity Holes

### Finding 5.1 — `--delete` rsync semantics can wipe marketplace `.git/` if destination misconfigured [HIGH] [Grounded]

**Evidence:** Step 3.8 (L203) specifies `DEFAULT_RSYNC_FLAGS=["-a", "--delete"]` and `_rsync_staging(staging, marketplace_plugin_dir)` invoking `rsync -a --delete <staging>/ <marketplace>/plugins/ironops-devops/`. The `--delete` is intentional mirror semantics.

**Hole:** If `<marketplace>` is misconfigured (env var resolves to marketplace repo root, not `marketplace/plugins/ironops-devops/`), `--delete` will OBLITERATE the marketplace repo including its `.git/` directory. There is NO guard in Step 3.8 that the rsync destination contains the literal `plugins/ironops-devops/` suffix. There is NO test verifying destination path safety.

**Severity:** HIGH — A subtly-wrong `--marketplace` CLI argument can destroy the marketplace repo's git history. T1 missed this entirely.

**Recommendation:** Add a guard in `_rsync_staging`: `assert str(marketplace_plugin_dir).endswith("plugins/ironops-devops"), f"rsync --delete refused: destination must end with 'plugins/ironops-devops' to prevent marketplace-repo wipeout, got: {marketplace_plugin_dir}"`. Add a unit test (note: file inventory shows no `test_publish.py` module — itself a gap) that monkeypatches the marketplace path to a wrong subdir and asserts the guard raises `PublishFailed` BEFORE rsync runs.

### Finding 5.2 — Stage 4 marketplace.json write can leave dirty working tree contaminating next build [MEDIUM] [Grounded]

**Evidence:** SPEC §7 Stage 4 L362-366 lists emission order: plugin.json → META.json → THIRD_PARTY_LICENSES.md → marketplace.json. Marketplace.json is emitted at `<marketplace-repo>/.claude-plugin/marketplace.json` (parent root). If `write_marketplace_json` writes to the marketplace tree BEFORE Stage 5 validate runs, then a Stage 5 failure leaves a stale marketplace.json on disk in the marketplace-repo working tree (not committed). FR-9 atomicity is preserved (HEAD unchanged), but `git add -A` in Step 3.8's next-build publish picks up the stale file.

**Severity:** MEDIUM — Working tree contamination across failed→next-build boundary. Subtle: contract "HEAD unchanged" is preserved while the next publish can ship stale data.

**Recommendation:** Either (a) Stage 4 writes marketplace.json to the STAGING dir, and Stage 6 PUBLISH rsyncs it to the marketplace as part of atomic publish; OR (b) Step 3.8's `_commit_and_push` runs `git -C <marketplace> reset --hard HEAD` at START to clean any leftover state. Add an integration test simulating: Stage 4 fails partway, next build runs, assert no stale data published.

### Finding 5.3 — `git push` rebase-and-retry can race local builds, publishing stale META.json SHAs [MEDIUM] [Grounded]

**Evidence:** Step 3.8 (L203) specifies retry-once on non-fast-forward via `git fetch + git rebase origin/<branch> + git push`. Step 7.2 (L351) workflow has `concurrency: ironops-publish` for CI. BUT a local `ironops build` run pointing at a real marketplace can race a CI build. The rebase merges newer marketplace state into older staging — if staging was generated against an older upstream SHA, the published META.json reports the older SHA while the working tree contains newer content.

**Severity:** MEDIUM — Local-execution race not addressed by CI concurrency. FR-9 atomicity preserved at git layer; correctness invariant (META.json SHA matches published content) broken.

**Recommendation:** Step 3.8 should refuse to rebase-and-retry if the marketplace HEAD that won the race has a different `builder_version`. After `git fetch`, parse the remote HEAD's commit message for `builder_version: <SHA>`; abort with `PublishFailed` if it differs. OR document local-execution race as out-of-scope (require all production publishes via CI only).

---

## 6. Confirmations Against T1 (where I AGREE with T1)

I agree with these T1 findings (subject to my own evidence checks):

- **T1 Finding 3.1 (AC-7 install-and-invoke missing):** Confirmed. Grep across TASKLIST for `claude plugin install ironops-devops` returns only Step 7.2's CI build context, never as a smoke-test verifier.
- **T1 Finding 3.2 (AC-9 guard-coverage report artifact missing):** Confirmed AND EXPANDED in my Finding 2.1 with row-by-row mapping.
- **T1 Finding 3.3 (NFR-2 timing budget not measured):** Confirmed. No test asserts wall-clock against 60s/300s targets.
- **T1 Finding 3.4 (NFR-8 backward-compat regression test):** Confirmed.
- **T1 Finding 4.1 (CLI entry-point `cli:main` vs D2's `cli:cli`):** Confirmed deliberate deviation.
- **T1 Finding 4.3 (NFR-4 strict-warnings underspecified):** Confirmed.
- **T1 Finding 4.4 (conftest mock fixture APIs not pinned):** Confirmed.
- **T1 Finding 5.1 (claude CLI install command unresolved):** Confirmed HIGH. My Finding 1.2 stacks on this — the upstream-clone auth path has the same shape of unresolved-at-task-time risk.
- **T1 Finding 5.5 (REGEN_GOLDEN CI chicken-and-egg):** Confirmed AND EXPANDED in my Finding 4.1 — the LOCAL execution path also breaks at Step 9.2.

---

## 7. Disagreements With T1 (where T1 over-called or missed nuance)

- **T1 Finding 4.2 (`@click.version_option` + `version()` subcommand redundancy, LOW):** I think T1 is correct they're redundant, but severity should be NEGLIGIBLE not LOW. Click users routinely encounter `--version` flag + `version` subcommand both (e.g., `git --version` vs `git version`). T1's recommendation to "decide" adds friction without benefit. Drop this finding.
- **T1 Finding 5.4 (Windows paths in path-escape parametrize, LOW):** T1 frames as maybe-drop. I would CONFIRM the Windows paths SHOULD stay — they're defense-in-depth for a future port or Windows-authored manifest. The parametrize is a 4-line addition with zero cost. T1's framing risks dropping a defensive test for no benefit.
- **T1 Finding 6.1 (§13 "~8 skills" vs Step 7.3 "10 skills", LOW):** I disagree on severity — this is MEDIUM minimum because AC-8 traceability table will be inconsistent. See my Finding 1.1 which extends to §10 N=26 and §6 example values. T1's LOW understates the spec-vs-impl gap.

---

## 8. Self-Reported Confidence

- citation_grounding: 5 — every finding cites SPEC line, TASKLIST line, or disposition reference; no [INFERRED] tags (Finding 1.2 cross-checked against actual Step 7.2/7.3 wording; Finding 2.1 cross-checked row-by-row against §9 L399-426).
- coverage_completeness: 4 — surveyed all 16 FRs, 9 NFRs, 10 ACs, all 26 §9 guard rows, all 9 tasklist phases; did not execute tests; did not read every research file in full; did not deeply probe FR-7 byte-identical invariant (T1 touched it).
- deviation_classification_clarity: 4 — HIGH for AC-9 row coverage gaps, rsync --delete destination guard, golden-fixture local bootstrap; MEDIUM for spec-version drift, SSH/HTTPS auth mismatch, Stage 2 no-op, marketplace.json placement contract, partial publish window, push race; LOW for `git remote show` shape, ordering brittleness, test inventory name brittleness, scaffolding ordering.
- risk_surface_coverage: 4 — probed structural seams T1 missed (upstream-clone auth, rsync --delete safety, Stage 4 emit-target ambiguity, push race vs concurrency, §10 fanout count drift, §9 row-by-row mapping); did not probe disk-full / network failure modes beyond spec §15.
- recommendation_actionability: 4 — every finding cites a specific Step number AND a concrete fix (add a guard, add a test, add a Phase 2 spec amendment, reorder steps); a few alternatives offered (e.g., HTTPS vs SSH-agent) which executor must choose.
- self_reported_confidence: 0.83
- rationale: "Found three HIGH structural issues T1 missed (11+ of 26 §9 rows have partial/zero coverage with no AC-9 artifact step; rsync --delete can wipe marketplace if destination misconfigured; golden-fixture local bootstrap path breaks at Step 9.2), three MEDIUM regression-risk holes (SSH-vs-HTTPS auth drift, Stage 4 marketplace.json placement contaminates working tree across failed builds, push race vs builder_version), plus LOW spec-vs-impl drift items. Distinct angle from T1's completion+operational focus. Did not execute tests or read all research files."

## 9. Inferred Claims Count

citations_total: 22
citations_inferred: 0
