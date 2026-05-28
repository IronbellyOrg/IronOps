# Research Note 04 — Test Patterns + Integration Points

**Status:** Complete
**Researcher:** researcher-04
**Topic:** Pytest patterns from IronClaude + integration-point subprocess shapes for IronOps
**Date:** 2026-05-27

## Purpose

Document concrete pytest idioms IronOps should adopt (Part A) and the subprocess
invocation shapes the IronOps builder needs (Part B). The task-builder will use
this to write per-test-file and per-module checklist items.

---

## PART A — pytest patterns from IronClaude

### A.1 — `tests/conftest.py` style (root fixtures)

**Source:** `/config/workspace/IronClaude/tests/conftest.py`

Key conventions IronOps should mirror:

1. **Top-of-file `collect_ignore` for optional-dep tests**
   — `conftest.py:13-15` uses a module-level list to skip test files that require
   non-declared deps (e.g. `hypothesis`). IronOps should adopt the same pattern
   for `test_smoke.py` if the `claude` CLI is not installed in CI.

2. **Session-scoped `autouse=True` pollution-snapshot fixture**
   — `conftest.py:28-79` captures a baseline of files in `docs/mistakes/` and
   the size of `docs/memory/solutions_learned.jsonl` at session start, then
   asserts on session teardown that nothing was mutated. Pattern for IronOps:
   if any builder test could pollute repo state (e.g. `dist/` writes), use the
   same `yield`-based capture. **Critical detail at lines 38-44:** the comment
   explicitly explains *why* this lives in `conftest.py` not in a test module —
   pytest fires `SETUP` for a session-scoped autouse fixture only at first
   collection of the module that owns it, so locating it in `conftest.py`
   ensures it runs before all test modules.

3. **Per-test autouse `monkeypatch.setenv` for redirecting writes to `tmp_path`**
   — `conftest.py:82-117` shows the canonical "redirect output dir into tmp"
   pattern: set `REFLEXION_OUTPUT_DIR=<tmp_path>/...` so any production code
   path resolving its storage dir from env will land in tmp instead of the
   real repo. IronOps equivalent: redirect any "staging dir" or "marketplace
   clone dir" env vars to `tmp_path` for all tests.

4. **Per-fixture mini-context fixtures**
   — `conftest.py:120-202` defines `sample_context`, `low_confidence_context`,
   `sample_implementation`, `failing_implementation` as named dicts. IronOps
   should adopt the same idiom for `valid_manifest`, `bad_schema_manifest`,
   `bad_empty_imports_manifest`, etc. — one fixture per failure category.

5. **`temp_memory_dir` builds a production-mirroring directory tree**
   — `conftest.py:206-225` constructs `<tmp_path>/docs/memory/` with seed files
   pre-written, returns the directory. IronOps equivalent: `temp_staging_dir`,
   `temp_marketplace_clone` fixtures that build a real-shape directory in
   `tmp_path` and return the `Path`.

### A.2 — CliRunner usage (Click commands under test)

**Source:** `/config/workspace/IronClaude/tests/cli/test_cli_registration.py`

Pattern:

```python
from click.testing import CliRunner
from superclaude.cli.main import main

@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()

def test_top_level_help_lists_eval_group(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0, result.output
    assert "eval" in result.output
```

Key idioms (`test_cli_registration.py:56-119`):

- **Fixture returns `CliRunner()`** — re-used across multiple tests.
- **`result.exit_code` is asserted with `result.output` as the failure message**
  (line 64): `assert result.exit_code == 0, result.output` — gives instant
  diagnosis when a test fails.
- **`frozenset` literal for expected command roster** (lines 31-47) — pinning
  the expected set so any accidental rename trips the test. Use the same
  shape for IronOps `EXPECTED_TOP_LEVEL_COMMANDS = frozenset({"build",
  "validate", "publish", "version", "doctor"})` or similar.
- **Both help-text AND Click-registry checks** (lines 84-104) — pin both
  surfaces because a docstring-only stub could pass the help-text check while
  failing the registry one. IronOps: assert `main.commands["build"]` exists
  AND `"build" in result.output`.
- **Smoke-test loop over the roster** (lines 107-118) — iterate the expected
  command names and invoke `--help` on each, asserting exit code 0. Cheap
  regression guard.

### A.3 — `tmp_path` / file-system fixture conventions

**Sources:**
- `/config/workspace/IronClaude/tests/cli/test_install_hooks.py:41-123`
  (`fake_source_hooks` fixture)
- `/config/workspace/IronClaude/tests/unit/test_cli_install.py:26-46`

Patterns:

1. **`fake_source_hooks` fixture stands up an entire mock source tree**
   (`test_install_hooks.py:41-123`):
   - Receives `(tmp_path, monkeypatch)`.
   - Constructs `<tmp_path>/pkg/hooks/{hooks.json, scripts/, ...}` with realistic
     content (a real-shape `hooks.json` literal at lines 56-83).
   - Uses `monkeypatch.setattr("module._get_hooks_source", lambda: ...)` to
     redirect the production code's source-locator function to point at the
     fake tree (lines 106-122).
   - **Returns the fake source root** so individual tests can inspect.

   IronOps equivalent: `fake_upstream_clone` fixture that builds a
   `<tmp_path>/upstream-clone/` tree mimicking the relevant slice of
   IronClaude (a few skill dirs + agents + commands), then monkeypatches
   `ironops.sources.git_clone` to copy from this fixture instead of calling
   real git.

2. **One-liner `target_settings` fixture** (`test_install_hooks.py:126-132`)
   creates a parent dir and returns a `Path` to a non-existent target file —
   pattern for "where the operation should write." IronOps: `target_staging`,
   `target_marketplace` fixtures.

3. **Direct `tmp_path` use for simple tests** (`test_cli_install.py:26-46`) —
   when a test only needs one writable dir, take `tmp_path` directly. No need
   to wrap in another fixture.

### A.4 — `monkeypatch` vs real subprocess

Two distinct patterns appear in IronClaude:

**Pattern 1 — `monkeypatch.setattr` on the I/O primitive** (`test_install_failures.py:25-26, 57-70`):

```python
def _raise_permission_error(*_args, **_kwargs):
    raise PermissionError("simulated read-only target")

def test_install_surfaces_failure_details_on_copy_error(
    tmp_path, monkeypatch, module, fn_name, empty_sentinel
):
    monkeypatch.setattr(shutil, "copy2", _raise_permission_error)
    ...
```

Use this for unit tests: replace the lowest-level I/O call (`shutil.copy2`,
`subprocess.run`, `os.replace`) with a stub that raises or returns a canned
value. Fast, hermetic. IronOps unit tests should use this for `subprocess.run`,
`shutil.copytree`, and the validator call.

**Pattern 2 — Real `subprocess.run` against the real CLI**
(`test_verify_sync_hooks.py:55-63`):

```python
def _run_verify_sync() -> subprocess.CompletedProcess:
    return subprocess.run(
        ["make", "verify-sync"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
```

Use this for integration tests: actually invoke `make`, `git`, or the
IronOps CLI as a subprocess; assert against `returncode`, `stdout`, `stderr`.
Slow but checks the real wiring. IronOps: integration tests should call
`subprocess.run(["uv", "run", "ironops", "build", ...])` against a
fake-upstream fixture.

**`shutil.which` pre-flight skip** (`test_verify_sync_hooks.py:43-52`):

```python
_HAS_JQ = shutil.which("jq") is not None
_HAS_MAKE = shutil.which("make") is not None

pytestmark = [
    pytest.mark.skipif(not _HAS_MAKE, reason="make required for verify-sync tests"),
    pytest.mark.skipif(not _HAS_JQ, reason="jq required by ..."),
]
```

IronOps **MUST** use this for `test_smoke.py` (gated on `claude` CLI being
installed) and any test that shells out to `rsync` or `git`.

**`@contextmanager` for safe in-place mutation + restore**
(`test_verify_sync_hooks.py:66-117`):

```python
@contextmanager
def _temporarily_replace_file(path: Path, new_content: str):
    original = path.read_text()
    try:
        path.write_text(new_content)
        yield
    finally:
        path.write_text(original)
```

When a test MUST mutate a real file (e.g. introduce a bad manifest), wrap
the mutation in a `@contextmanager` with `try/finally` restore. IronOps
should use this only when `tmp_path`-based fixtures can't reach the
production code path (rare; prefer fixtures).

### A.5 — Parametrization

**Source:** `/config/workspace/IronClaude/tests/cli/test_install_failures.py:29-57`

```python
_INSTALLER_CASES = [
    pytest.param(install_templates_mod, "install_templates",
                 "No templates were installed", id="templates"),
    pytest.param(install_core_mod, "install_core_files",
                 "No core framework files were installed", id="core"),
    ...
]

@pytest.mark.parametrize("module,fn_name,empty_sentinel", _INSTALLER_CASES)
def test_install_surfaces_failure_details_on_copy_error(
    tmp_path, monkeypatch, module, fn_name, empty_sentinel
):
    ...
```

Idioms:

- **`pytest.param(..., id="<name>")` for readable test IDs** — appears in the
  test runner output as `test_x[templates]` instead of mystery indices.
- **Tuple-shape unpacking in `@parametrize`** — comma-separated names match
  function arg names.
- **Cases hoisted to module-level constants** — easy to extend, easy to
  audit.

IronOps should parametrize:
- `test_negative.py` over all `bad-*.yaml` manifest fixtures (one `pytest.param`
  per fixture, `id="bad-schema"`, `id="bad-empty-imports"`, etc.).
- `test_errors.py` over every NFR-7 categorical code.

### A.6 — Negative-test patterns (malformed input)

**Sources:**
- `test_install_failures.py:57-107` — exception injection via `monkeypatch.setattr`
- `test_install_hooks.py:299-309` — malformed input file
- `test_install_hooks.py:317-334` — permission-denied via `os.chmod` on parent

Idioms:

1. **Write the bad input directly to `tmp_path`** (line 300):
   `target_settings.write_text("{not valid json...")` — no need to construct
   a fixture for a one-line bad input.

2. **Assert lowercase substrings in error messages** (line 304):
   `assert "malformed" in msg.lower()` — robust to capitalization changes.

3. **Verify side-effects didn't happen** (lines 307-309): assert the original
   file is unchanged after the refuse. IronOps: after a manifest-validate
   failure, assert `marketplace_repo HEAD` is unchanged (FR-9 invariant).

4. **`os.chmod` + `try/finally` for permission tests** (lines 320-334):

```python
os.chmod(parent, 0o555)
try:
    ok, msg = install_hooks(...)
    assert not ok
    assert "permission" in msg.lower() or "denied" in msg.lower()
finally:
    os.chmod(parent, 0o755)
```

   The `finally` is mandatory so pytest can clean up `tmp_path`.

### A.7 — Snapshot/golden-output testing

IronClaude does NOT have an explicit snapshot-testing library (no
`pytest-snapshot` / `syrupy` in `pyproject.toml` as of this read). The
closest pattern is **regression-pin testing** in
`test_install_hooks.py:438-465`:

```python
def test_real_hooks_json_gates_write_in_pre_tool_use():
    """Pin the matcher tools list so the gated set doesn't drift silently."""
    real_hooks = (
        Path(__file__).resolve().parents[2]
        / "src" / "superclaude" / "hooks" / "hooks.json"
    )
    data = json.loads(real_hooks.read_text())
    ...
    assert "Edit" in matcher_tools
    assert "Write" in matcher_tools
    assert "mcp__serena__replace_content" in matcher_tools
```

For IronOps golden-output testing (AC-2), recommended approach:

**Option A (preferred):** commit a `tests/fixtures/golden/v0_1_plugin_tree.json`
listing the expected files + their SHA256s. The integration test runs the
builder against the snapshot fixture, walks the rendered tree, computes
SHA256 of each file (excluding `META.json.built_at`), and diffs against the
golden JSON.

**Option B:** commit the full rendered tree under
`tests/fixtures/golden/v0_1_plugin_tree/` and use `dircmp` or `filecmp` to
compare. More disk, easier debugging.

Either way, the test should provide a "regenerate golden" flag:
```python
if os.environ.get("REGEN_GOLDEN"):
    write_golden(...)
    pytest.skip("regenerated golden — re-run without REGEN_GOLDEN")
```

---

## PART B — Integration-Point Subprocess Shapes

For each external command the builder invokes, this section gives:
(1) the exact command, (2) expected exit-code semantics, (3) stderr handling,
(4) failure-mode mapping to the NFR-7 categorical codes
(`MANIFEST_INVALID`, `UNRESOLVED_IMPORT`, `CO_IMPORT_MISSING`,
`VALIDATE_FAILED`, `PATH_ESCAPE`, `UPSTREAM_CLONE_FAILED`, `SELF_OVERWRITE`,
`BUILDER_DIRTY_TREE`).

All commands run under `subprocess.run(..., capture_output=True, text=True,
timeout=<N>, check=False)`. Builder code inspects `.returncode`, `.stdout`,
`.stderr` explicitly — never `check=True` (we need structured error mapping,
not exception propagation).

### B.1 — `git clone --depth=1` (FR-2, Stage 1)

**Command:**
```
git clone --depth=1 <upstream-url> <scratch-dir>
```

**Caller:** `src/ironops/sources.py::clone_upstream(source_id, url, scratch_root) -> Path`

**Exit codes:**
- `0` — success. `<scratch-dir>` exists and contains `.git/`.
- `128` — typical for clone failures (auth, missing repo, network).
- Other non-zero — network/timeout/disk.

**stderr handling:** capture; on non-zero, surface verbatim in the
`UPSTREAM_CLONE_FAILED` log artifact. Truncate to first 2KB if larger.

**Timeout:** 60s (NFR-2 budget allows it; clone of small IronClaude is <10s
in practice).

**Failure-mode mapping:** any non-zero exit → `UPSTREAM_CLONE_FAILED`.

**Implementation note:** must clone to a brand-new dir that does NOT exist
(git clone fails if the target already exists and is non-empty). The
scratch root should be `tempfile.mkdtemp(prefix="ironops-clone-")` and the
clone path `<scratch-root>/<source-id>/`.

**Cleanup:** scratch dir removed in `finally` of the pipeline orchestrator
(`Risks` row 4 of spec — disk-full mitigation).

### B.2 — `git -C <scratch-dir> rev-parse HEAD` (FR-2-A2, Stage 1)

**Command:**
```
git -C <scratch-dir> rev-parse HEAD
```

**Caller:** `src/ironops/sources.py::resolve_sha(scratch_dir) -> str`

**Exit codes:**
- `0` — `stdout.strip()` is the 40-char SHA.
- non-zero — broken clone (impossible if B.1 succeeded; assert/raise).

**stderr handling:** if non-zero, treat as an internal-consistency bug and
raise `RuntimeError` (not a categorical code — this should be unreachable).

**Output validation:** assert `len(stdout.strip()) == 40` and all chars in
`0-9a-f`. Reject otherwise.

**Failure-mode mapping:** if B.1 succeeded but rev-parse fails →
`UPSTREAM_CLONE_FAILED` (clone produced an invalid working tree).

### B.3 — `git -C <scratch-dir> remote show origin` (FR-2-A3, Stage 1)

**Command:**
```
git -C <scratch-dir> remote show origin
```

**Caller:** `src/ironops/sources.py::resolve_default_branch(scratch_dir) -> str`

**Why not `git symbolic-ref refs/remotes/origin/HEAD`?** That symbolic ref
is set only on full clones, not on `--depth=1` shallow clones. `remote show
origin` reaches out to the remote and reports the actual default branch.

**Caveat — network dependency:** this command requires network. Cache the
result per `(url)` in builder state to avoid re-calling for the same source.

**Exit codes:**
- `0` — `stdout` contains `HEAD branch: <name>`. Parse with regex
  `^\s*HEAD branch:\s+(\S+)\s*$`.
- non-zero — auth/network failure.

**Failure-mode mapping:** non-zero → `UPSTREAM_CLONE_FAILED` (same category as
B.1 — upstream unreachable).

**Spec note:** FR-2-A3 forbids assuming "main" or "master." If parse fails
even on exit 0, raise `UPSTREAM_CLONE_FAILED` rather than silently defaulting.

### B.4 — `git -C <scratch-dir> status --porcelain` (FR-3-A1, NFR-9)

**Command:**
```
git -C <scratch-dir> status --porcelain
```

**Caller:** `src/ironops/sources.py::assert_clean(scratch_dir) -> None`

**Called from:** Stage 7 (post-render verification) — confirms the builder
did NOT mutate the upstream clone.

**Exit codes:**
- `0` — always (status itself doesn't fail on dirty state; dirty just shows
  up in stdout).
- non-zero — broken clone (re-raise).

**Decision logic:**
- `stdout.strip() == ""` → clean → pass.
- non-empty stdout → builder violated FR-3. This is a builder bug, not a
  user error. **Map to `RuntimeError` (internal invariant violation)**, NOT
  to a categorical code. Spec NFR-7 codes are for user-visible failures;
  FR-3 violation is a builder-code bug that requires a code fix.

### B.5 — `git -C <ironops-repo> status --porcelain` (FR-12, Stage 0)

**Command:**
```
git -C <ironops-repo-root> status --porcelain
```

**Caller:** `src/ironops/pipeline.py::preflight()`

**Exit codes:** same as B.4.

**Decision logic:**
- `stdout.strip() == ""` → clean → proceed to Stage 1.
- non-empty → abort with categorical code `BUILDER_DIRTY_TREE`.

**Spec ref:** SPEC §9 row 26 (`IronOps working tree clean` guard); SPEC §7
Stage 0; FR-12.

**Override:** must be bypassable with a `--allow-dirty` CLI flag for local
development (otherwise the builder is unusable on a dev machine with any
WIP). CI runs WITHOUT the flag.

### B.6 — `claude plugin validate <staging-dir>` (FR-5, Stage 5)

**Command:**
```
claude plugin validate <staging-dir>
```

**Caller:** `src/ironops/validate.py::validate_plugin(staging_dir) -> tuple[bool, str]`

**Exit codes:**
- `0` — plugin valid. Output captured to build log per FR-5-A2.
- non-zero — validation errors. NFR-4 also requires zero warnings, but the
  `claude` CLI exit code distinguishes only error/no-error; warnings are
  emitted to stdout/stderr. **Parser must scan stdout/stderr for
  warning-pattern lines** and fail the build if any are present
  (NFR-4 strict-warnings interpretation).

**stderr handling:** capture; persist to a build-log artifact (FR-5-A2,
NFR-7 30-day retention). On failure, stderr is the primary signal.

**Timeout:** 30s (validator is local; should be fast).

**Failure-mode mapping:**
- exit code ≠ 0 → `VALIDATE_FAILED`.
- exit 0 but warnings present in output → `VALIDATE_FAILED` (NFR-4 strict).

**`claude` binary may be absent:**
- Unit tests: monkeypatch `subprocess.run` to return a fake
  `CompletedProcess` with `returncode=0`, `stdout=""`, `stderr=""`.
- Integration tests: `pytestmark = pytest.mark.skipif(not shutil.which("claude"),
  reason="claude CLI not installed")` at top of test module.
- CI workflow: explicit `Install Claude CLI` step before tests; install via
  `npm install -g @anthropic-ai/claude-code` or whatever the current install
  command is (research note: confirm during build, the install path may
  evolve).

**Artifact retention:** the captured validator output goes to
`dist/build-log.txt` (relative to staging) which the GH Actions workflow
uploads as a build artifact with retention 30 days.

### B.7 — `rsync -a --delete <staging>/ <marketplace-clone>/plugins/ironops-devops/` (FR-9, Stage 6)

**Command:**
```
rsync -a --delete <staging-dir>/ <marketplace-clone>/plugins/ironops-devops/
```

**Note the trailing slashes** — `<staging>/` (with slash) copies the
*contents* into the destination; without the trailing slash rsync would
nest the staging dir name inside the destination. Wrong slashes here = wrong
plugin tree structure.

**Caller:** `src/ironops/publish.py::sync_to_marketplace(staging, marketplace_clone) -> None`

**Exit codes:**
- `0` — sync succeeded.
- non-zero — rsync error (disk full, permission, malformed paths).

**stderr handling:** capture; rsync error messages are human-readable. On
non-zero, the staging dir is preserved (so the operator can inspect) and the
marketplace clone is rolled back via `git -C <marketplace-clone> reset
--hard HEAD` so partial-sync state doesn't leak into the next attempt.

**Failure-mode mapping:** non-zero → no NFR-7 code is a direct match. Use a
new code `PUBLISH_FAILED` OR re-use `VALIDATE_FAILED` semantically (since
the publish stage is post-validate). **Recommendation:** add `PUBLISH_FAILED`
to the NFR-7 enum (this is a spec gap — flag during task execution).

**`--delete` semantics:** removes files in destination that don't exist in
source. This is intentional: the marketplace plugin tree should exactly
mirror the staging tree on each build (so removing a manifest entry
removes the file in the published plugin). The publish dir is
`plugins/ironops-devops/` which has no `.git` inside it (the marketplace
repo's `.git` is at `<marketplace-clone>/.git`, one level up). Safe.

### B.8 — `git add/commit/push` on marketplace clone (FR-9, Stage 6)

**Sequence (each is a separate `subprocess.run`, in order):**

```
git -C <marketplace-clone> add -A
git -C <marketplace-clone> status --porcelain      # any changes staged?
git -C <marketplace-clone> commit -m "ironops-devops: built from <ironops-sha> | sources: ironclaude@<resolved-sha>"
git -C <marketplace-clone> push origin main
```

**Caller:** `src/ironops/publish.py::publish_to_marketplace(...)`

**Step-by-step exit handling:**

1. **`add -A`** — exit 0 expected. non-zero is malformed repo; raise.

2. **`status --porcelain` after add** — if `stdout.strip() == ""`, NO
   changes staged. This means the build produced byte-identical output to
   the previous publish. **Behavior:** SKIP commit + push, log "no changes
   to publish", exit 0. **Do NOT create an empty commit.**

3. **`commit -m "..."`** — exit 0 expected. Commit message MUST contain:
   - The IronOps builder SHA (`META.json.builder_version`).
   - At least one source SHA (`sources[0].resolved_sha`).
   Per AC-6 verification.

4. **`push origin main`** — exit 0 expected.
   - non-zero typical cause: non-fast-forward (someone else pushed first).
     **Behavior:** retry with `git fetch + git rebase origin/main + git push`
     once. If still fails, abort with `PUBLISH_FAILED`. SPEC §15 mentions
     `concurrency: ironops-publish` GH Actions concurrency group as the
     primary mitigation; the retry is defense-in-depth.
   - non-zero on auth: surface stderr verbatim; abort with `PUBLISH_FAILED`.

**Failure-mode mapping:** any commit/push failure → `PUBLISH_FAILED` (new
NFR-7 code recommended; see B.7).

### B.9 — Mocking strategies summary

| Integration point | Unit-test mock | Integration-test approach |
|---|---|---|
| B.1 `git clone --depth=1` | `monkeypatch.setattr(ironops.sources, "subprocess_run", fake_clone)` that copies a fixture dir into the scratch dir | clone from a `tests/fixtures/ironclaude-snapshot/` bare repo created via `git init --bare` |
| B.2 `git rev-parse HEAD` | `fake_clone` also writes a known SHA file; `resolve_sha` reads it | real call against fixture clone |
| B.3 `git remote show origin` | `monkeypatch.setattr` returns fake stdout `"HEAD branch: main\n"` | real call against fixture clone with `git symbolic-ref` set in setup |
| B.4 `git status --porcelain` on upstream clone | `monkeypatch` returns empty stdout for clean, non-empty for dirty | real call after render |
| B.5 `git status --porcelain` on IronOps repo | `monkeypatch` returns canned response | real call against `tmp_path` git repo created via `git init` + commit |
| B.6 `claude plugin validate` | `monkeypatch.setattr` returns canned `CompletedProcess` | `pytest.mark.skipif(not shutil.which("claude"))` + real call against rendered staging |
| B.7 `rsync` | `monkeypatch.setattr(ironops.publish, "subprocess_run", fake_rsync)` that does `shutil.copytree` | real `rsync` call; fixture marketplace clone via `git init` in `tmp_path` |
| B.8 `git add/commit/push` | `monkeypatch` returns canned exit 0; verifies the commit-message string was assembled correctly | local fixture remote: `git init --bare <tmp_path>/marketplace-remote.git`, `git clone` into another `tmp_path` dir, push to the bare remote, verify post-push state |

### B.10 — Hermetic fixture pattern: `tests/fixtures/ironclaude-snapshot/`

**Rationale:** CI cannot clone IronClaude on every test run (network + auth
+ pollution). The hermetic fixture is a small, version-controlled
representative slice.

**Recommended structure:**

```
tests/fixtures/ironclaude-snapshot/
├── README.md                 # documents the snapshot's source commit
├── src/
│   └── superclaude/
│       ├── agents/
│       │   └── devops-architect.md          # 1 of the 11 v0.1 agents
│       ├── skills/
│       │   └── sc-troubleshoot-protocol/
│       │       └── SKILL.md                 # 1 of the 8 v0.1 skills
│       └── commands/
│           └── troubleshoot.md              # 1 of the 7 v0.1 commands
```

**Fixture wiring (in `tests/conftest.py`):**

```python
@pytest.fixture(scope="session")
def ironclaude_fixture_repo(tmp_path_factory) -> Path:
    snap = Path(__file__).parent / "fixtures" / "ironclaude-snapshot"
    repo_dir = tmp_path_factory.mktemp("ironclaude-fixture-repo")
    subprocess.run(["git", "init", "--quiet", str(repo_dir)], check=True)
    shutil.copytree(snap / "src", repo_dir / "src")
    subprocess.run(["git", "-C", str(repo_dir), "add", "-A"], check=True)
    subprocess.run([
        "git", "-C", str(repo_dir),
        "-c", "user.email=ironops@test",
        "-c", "user.name=ironops",
        "commit", "--quiet", "-m", "snapshot",
    ], check=True)
    return repo_dir
```

Test bodies then use `file://<repo_dir>` as the `url` in their test manifest,
exercising the real `git clone --depth=1` code path against the fixture
repo. Hermetic, no network.

**Snapshot maintenance:** when IronClaude reorgs paths or adds a new agent
to the v0.1 shortlist, the snapshot fixture must be updated. Document this
in `tests/fixtures/ironclaude-snapshot/README.md`. Recommended cadence:
update when the v0.1 manifest changes, OR when a major IronClaude release
adds shortlist components.

---

## TEST-FILE IMPLEMENTATION PLAN

Mapping every test file from RECOMMENDED_OUTPUTS (research-notes.md:151-160)
to the patterns above. Each row tells the task-builder exactly what
checklist items to write for that test file.

| Test file | Patterns to apply | Test cases (one per row) |
|---|---|---|
| `tests/conftest.py` | A.1 — root fixtures | `valid_manifest_yaml` fixture, `bad_*_manifest_yaml` fixtures (one per failure mode), `ironclaude_fixture_repo` (session-scoped, B.10), `temp_staging_dir`, `temp_marketplace_clone`, `monkeypatch.setenv` autouse for redirecting any IRONOPS_*_DIR env vars to tmp_path |
| `tests/unit/test_manifest.py` | A.5 parametrize, A.6 negative | `test_valid_manifest_parses`, `test_missing_schema_version_rejected`, `test_wrong_schema_version_rejected` (parametrized over `["999", "1.0", "1.x", 1]`), `test_empty_imports_rejected`, `test_missing_imports_rejected`, `test_self_overwrite_target_rejected` (parametrized over `[".claude-plugin/plugin.json", "META.json", "THIRD_PARTY_LICENSES.md"]`), `test_unknown_kind_rejected`, `test_missing_required_field_per_import`. FRs: FR-1, FR-14, FR-15, FR-16 |
| `tests/unit/test_sources.py` | A.3 fake-source fixture, A.4 pattern 1 (monkeypatch on `subprocess.run`) | `test_clone_upstream_invokes_correct_git_command` (assert argv shape), `test_clone_failure_maps_to_UPSTREAM_CLONE_FAILED`, `test_resolve_sha_returns_40_hex_chars`, `test_resolve_sha_rejects_short_output`, `test_resolve_default_branch_parses_remote_show`, `test_resolve_default_branch_no_main_assumption` (assert no hardcoded "main" or "master" anywhere in the module via `inspect.getsource`), `test_assert_clean_passes_on_empty_porcelain`, `test_assert_clean_raises_on_dirty`. FRs: FR-2, FR-3, NFR-9 |
| `tests/unit/test_render.py` | A.3 fake-upstream fixture, A.6 negative | `test_file_import_copies_byte_identical`, `test_directory_import_fans_out_to_all_files`, `test_path_escape_rejected` (parametrized over `["../../etc", "/etc/passwd", "C:\\Windows", "..\\..\\windows"]`), `test_claude_plugin_root_variable_recognized` (passes), `test_co_import_satisfied_passes`, `test_co_import_missing_command_skill_fails_with_CO_IMPORT_MISSING`, `test_co_import_orphan_skill_warns_not_fails`. FRs: FR-4, FR-7-A2, FR-8 |
| `tests/unit/test_metadata.py` | A.3, A.7 regression-pin | `test_plugin_json_omits_version_key` (FR-13-A1), `test_meta_json_schema_validates` (jsonschema check against §6), `test_meta_json_built_at_is_iso8601_utc`, `test_meta_json_enumerates_every_emitted_file` (FR-6-A1), `test_meta_json_builder_version_is_40_hex` (FR-6-A2), `test_marketplace_json_lists_ironops_devops_only` (FR-10), `test_third_party_licenses_md_present_and_references_ironclaude` (FR-11-A1) |
| `tests/unit/test_errors.py` | A.5 parametrize | Parametrize over every NFR-7 code: `MANIFEST_INVALID`, `UNRESOLVED_IMPORT`, `CO_IMPORT_MISSING`, `VALIDATE_FAILED`, `PATH_ESCAPE`, `UPSTREAM_CLONE_FAILED`, `SELF_OVERWRITE`, `BUILDER_DIRTY_TREE`, plus the recommended `PUBLISH_FAILED`. Assert each is a distinct integer exit code, each has a one-line stderr summary template, each is documented in the `--help` output of `ironops build`. NFR-7. |
| `tests/integration/test_pipeline.py` | A.4 pattern 2 (real subprocess), B.10 hermetic fixture | `test_end_to_end_build_against_fixture` — full Stage 0..7 against `ironclaude_fixture_repo`, asserts staging dir exists, validator was called (if `claude` available; skip otherwise), publish happened, marketplace clone has one new commit. Also `test_backtoback_build_skips_empty_commit` (B.8 no-changes path). Covers all FRs at integration level. |
| `tests/integration/test_atomicity.py` | A.4 pattern 1 (monkeypatch mid-flight), A.6 | `test_validate_failure_leaves_marketplace_unchanged` (monkeypatch `validate.validate_plugin` to return `(False, "fake")`, then assert `git -C marketplace_clone log -1` SHA is unchanged from pre-build), `test_publish_failure_rolls_back_marketplace_clone` (monkeypatch the `rsync` subprocess call to raise mid-sync, assert `git -C marketplace_clone status` is clean post-failure). FR-9. |
| `tests/integration/test_negative.py` | A.5 parametrize over all `bad-*.yaml` fixtures | Parametrize: each `bad-*.yaml` fixture file, each expected categorical exit code. For each: invoke `ironops build --manifest <bad-fixture>`, assert exit code matches expected NFR-7 code, assert stderr contains the one-line summary, assert marketplace clone HEAD unchanged. AC-10. |
| `tests/integration/test_golden_output.py` | A.7 golden snapshot, B.10 fixture | `test_v0_1_rendered_tree_matches_golden` — run builder against the fixture-snapshot manifest, then walk rendered tree and compare each file's SHA256 against the committed `tests/fixtures/golden/v0_1_plugin_tree.json`. Skip `META.json.built_at` from the hash. Support `REGEN_GOLDEN=1` env var to write the golden fixture instead of asserting (regen-then-skip pattern). AC-2. |
| `tests/integration/test_smoke.py` | A.4 `shutil.which` skip | `pytestmark = pytest.mark.skipif(not shutil.which("claude"), reason="claude CLI not installed")`. Run full build → install plugin via `claude plugin marketplace add <tmp> && claude plugin install ironops-devops@ironops` → assert `/ironops-devops:troubleshoot` is discoverable (`claude plugin details ironops-devops` exit 0). AC-7. |

---

## SUMMARY

**Status:** Complete

**Part A (pytest patterns from IronClaude):** documented 7 pattern categories
(conftest style, CliRunner, tmp_path fixtures, monkeypatch vs real subprocess,
parametrization, negative tests, snapshot/golden) with file:line citations
to `tests/conftest.py`, `tests/cli/test_cli_registration.py`,
`tests/cli/test_install_failures.py`, `tests/cli/test_verify_sync_hooks.py`,
`tests/cli/test_install_hooks.py`, `tests/unit/test_cli_install.py`,
`tests/unit/test_confidence.py`, `tests/integration/test_pytest_plugin.py`.

**Part B (integration points):** documented 8 subprocess invocations (B.1–B.8)
with exact command shape, exit-code semantics, stderr handling, and NFR-7
failure-mode mapping. Identified one spec gap: `PUBLISH_FAILED` is needed
as an NFR-7 code (rsync/git-push failures don't map cleanly to the
existing 8 codes). Documented hermetic fixture pattern (B.10) for
`tests/fixtures/ironclaude-snapshot/` and mocking strategies (B.9) per
integration point.

**Test-file implementation plan:** mapped all 11 test files (conftest +
5 unit + 5 integration) from RECOMMENDED_OUTPUTS to concrete test cases
with FR references. The task-builder can write one checklist item per
test case in the test-file implementation phase.

**Key cross-cutting recommendations for the task-builder:**

1. **Spec gap to flag:** add `PUBLISH_FAILED` to NFR-7 categorical codes.
   Currently the rsync/git-push failure has no clean mapping.

2. **`claude` CLI dependency:** every test path that calls
   `claude plugin validate` MUST be guarded by `shutil.which("claude")`
   skipif OR mocked. The CI workflow installs the CLI before running tests.

3. **Hermetic fixture is mandatory:** never let CI clone the real
   IronClaude repo per test. The `tests/fixtures/ironclaude-snapshot/`
   pattern with a `tmp_path_factory`-scoped local bare repo is the
   only sustainable path.

4. **Atomicity testing requires monkeypatch mid-flight:** `test_atomicity.py`
   is the hardest test surface — it requires injecting a failure between
   Stage 5 (validate) and Stage 6 (publish), or mid-Stage-6. Pattern: spawn
   the orchestrator with `monkeypatch.setattr(ironops.publish, "rsync_sync",
   side_effect=RuntimeError)` and assert the marketplace-clone-HEAD
   invariant.

5. **The B.8 "no-changes → skip commit" path needs an explicit test** in
   `test_pipeline.py` — back-to-back builds with no manifest/upstream
   changes must NOT create empty commits on the marketplace repo.
