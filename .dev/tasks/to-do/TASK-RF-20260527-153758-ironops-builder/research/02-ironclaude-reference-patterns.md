# Research: IronClaude Patterns & Conventions (Reference for IronOps Adaptation)

**Status:** In Progress
**Researcher:** researcher-02 (Patterns & Conventions)
**Date:** 2026-05-27
**Scope:** Extract patterns from IronClaude tooling that IronOps should ADAPT (not copy).

## Critical Caveats

- `scripts/build_superclaude_plugin.py` is **partially broken** (references a nonexistent manifest dir). Pattern reference only — do NOT copy the broken portions.
- `scripts/sync_from_framework.py` solves a **different problem** (whole-repo sync with name rewriting) than IronOps needs (manifest allowlist, byte-identical copy). Extract its **orchestration shape**, not its logic.

---

## 1. Project Layout

### Pattern 1.1 — `src/<package>/` layout with hatchling

**Source:** `/config/workspace/IronClaude/pyproject.toml:72-77`

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/superclaude"]
include = [
    "src/**",
    "plugins/**",
]
```

**Why relevant to IronOps:** IronOps is a single-purpose Python tool that will be `pipx install`-ed. The `src/<package>/` layout is the modern Python packaging convention and works cleanly with hatchling (zero-config PEP 517).

**Adapt for IronOps:**
- Use `src/ironops/` as the package root.
- Drop the `force-include` block (`pyproject.toml:79-81`) — that's a SuperClaude-specific hack to ship source files at runtime. IronOps does not need it.
- Drop `plugins/**` from `include` — IronOps has no plugin directory.

### Pattern 1.2 — CLI subpackage layout

**Source:** `/config/workspace/IronClaude/src/superclaude/cli/main.py:1-15`

**Structure observed:** `src/superclaude/cli/` is the CLI subpackage; `main.py` is the entry, each subcommand lives in a separate module (`install_agents.py`, `install_commands.py`, etc.) and is imported lazily inside the command function or registered via `main.add_command()` at module load.

**Why relevant to IronOps:** IronOps will have a small CLI (likely `ironops build`, `ironops verify`); a CLI subpackage with one module per subcommand keeps imports cheap and testing trivial.

**Adapt for IronOps:**
- Use `src/ironops/cli/main.py` as entry, with `src/ironops/cli/build.py` (and similar) for each subcommand.
- Skip the deferred-import-to-avoid-circular pattern (`src/superclaude/cli/main.py:400-426`) — that's load-bearing for SuperClaude's large surface; IronOps will not have circular imports because it is small.

---

## 2. pyproject.toml Shape

### Pattern 2.1 — Build system + project metadata

**Source:** `/config/workspace/IronClaude/pyproject.toml:1-32`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "superclaude"
version = "4.2.0"
description = "..."
readme = "README.md"
license = {text = "MIT"}
authors = [{name = "...", email = "..."}]
requires-python = ">=3.10"
keywords = [...]
classifiers = [
    "Development Status :: 4 - Beta",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    ...
]
```

**Why relevant to IronOps:** Standard, copy-shaped. Hatchling is the project's chosen build backend; staying consistent reduces cognitive load for contributors who move between IronClaude and IronOps.

**Adapt for IronOps:**
- `name = "ironops"`, `version = "0.1.0"` (v0.1 per the track goal).
- Drop classifiers about pytest/AI; IronOps is an infra tool, not a pytest plugin.
- `requires-python = ">=3.10"` — match IronClaude.

### Pattern 2.2 — Dependencies + dev optional-deps

**Source:** `/config/workspace/IronClaude/pyproject.toml:34-56`

```toml
dependencies = [
    "pytest>=7.0.0",
    "click>=8.0.0",
    "rich>=13.0.0",
    "pyyaml>=6.0",
    "jsonschema>=4.0.0",
    "pexpect>=4.9",
]

[project.optional-dependencies]
dev = [
    "pytest-cov>=4.0.0",
    "pytest-benchmark>=4.0.0",
    "black>=22.0",
    "ruff>=0.1.0",
    "mypy>=1.0",
]
```

**Why relevant to IronOps:** Established dep pattern (click for CLI, rich for output, ruff for lint, mypy optional).

**Adapt for IronOps:**
- Runtime deps for v0.1 builder: just `click>=8.0.0`. Possibly `rich>=13.0.0` for nicer output, but **start without it** (prefer simpler proposals — `feedback_prefer_simpler_proposals.md`). Stdlib `json`, `shutil`, `pathlib`, `subprocess`, `argparse` cover the byte-identical-copy builder.
- Dev deps: `pytest>=7.0.0`, `pytest-cov>=4.0.0`, `ruff>=0.1.0`. Drop pytest-benchmark, scipy, mypy for v0.1.
- Drop `pexpect` (SuperClaude-specific, used by the cliEval PTY driver).
- Drop `pyyaml`/`jsonschema` unless IronOps' manifest format ends up being YAML with schema validation; for v0.1 manifest, JSON is simpler.

### Pattern 2.3 — Entry point registration

**Source:** `/config/workspace/IronClaude/pyproject.toml:64-66`

```toml
[project.scripts]
superclaude = "superclaude.cli.main:main"
```

**Why relevant to IronOps:** This is the canonical hatchling pattern for registering a console script.

**Adapt for IronOps:**

```toml
[project.scripts]
ironops = "ironops.cli.main:main"
```

Drop `[project.entry-points.pytest11]` (`pyproject.toml:69-70`) — IronOps is not a pytest plugin.

### Pattern 2.4 — Ruff configuration

**Source:** `/config/workspace/IronClaude/pyproject.toml:177-197`

```toml
[tool.ruff]
line-length = 88
target-version = "py310"
exclude = ["docs/"]
extend-exclude = [".dev/", "tests/audit/fixtures/syntax_error.py"]

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "TID"]
ignore = ["E501", "N818"]
```

**Why relevant to IronOps:** Established ruff baseline for the org. Same line-length, same target-version simplifies tooling consistency.

**Adapt for IronOps:**
- Keep `line-length = 88`, `target-version = "py310"`, `select = ["E", "F", "I", "N", "W"]`.
- Drop `TID` (tidy-imports) until needed; drop `N818` ignore (no legacy exception names yet).
- Drop `flake8-tidy-imports.banned-api` block (`pyproject.toml:207-210`) — that's the SuperClaude-specific anthropic-SDK ban; irrelevant.
- Add `extend-exclude = [".dev/"]` if IronOps adopts the same `.dev/` artifact convention.

### Pattern 2.5 — Pytest configuration

**Source:** `/config/workspace/IronClaude/pyproject.toml:101-110`

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = ["-v", "--strict-markers", "--tb=short"]
```

**Why relevant to IronOps:** Sensible default pytest config; `--strict-markers` catches typos in `@pytest.mark.*` usage.

**Adapt for IronOps:** Copy verbatim. Drop the huge `markers = [...]` list (`pyproject.toml:111-135`) — IronOps starts with zero custom markers.

### Pattern 2.6 — Coverage configuration

**Source:** `/config/workspace/IronClaude/pyproject.toml:137-158`

```toml
[tool.coverage.run]
source = ["src/superclaude"]
omit = ["*/tests/*", "*/test_*", "*/__pycache__/*", "*/.*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
    ...
]
show_missing = true
```

**Why relevant to IronOps:** Standard coverage exclusions.

**Adapt for IronOps:** Copy verbatim; change `source = ["src/ironops"]`.

---

## 3. Makefile Target Patterns

### Pattern 3.1 — Core dev targets

**Source:** `/config/workspace/IronClaude/Makefile:1-63`

Key targets and their shapes:

- `install` (lines 5-10): `uv pip install -e ".[dev]"` — editable mode + dev extras.
- `test` (lines 13-15): `uv run pytest`.
- `lint` (lines 48-50): `uv run ruff check .`.
- `format` (lines 53-55): `uv run ruff format .`.
- `clean` (lines 58-63): removes `build/`, `dist/`, `*.egg-info`, and `find`-clears `__pycache__`, `.pytest_cache`, `.ruff_cache`.

```makefile
.PHONY: install test doctor verify clean lint format ... help
SHELL := /bin/bash

install:
	uv pip install -e ".[dev]"

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
```

**Why relevant to IronOps:** Org-standard Makefile target names. Contributors moving between repos expect `make test`, `make lint`, `make format`, `make clean` to do the same thing everywhere.

**Adapt for IronOps:** Copy verbatim. The set IronOps needs: `install`, `test`, `lint`, `format`, `clean`, `build`, `help`.

### Pattern 3.2 — Build target

**Source:** `/config/workspace/IronClaude/Makefile:68-71`

```makefile
.PHONY: build-plugin
build-plugin: ## Build SuperClaude plugin artefacts into dist/
	@echo "Building SuperClaude plugin from unified sources..."
	@uv run python scripts/build_superclaude_plugin.py
```

**Why relevant to IronOps:** IronOps' core purpose IS the builder. This target is the closest analog.

**Adapt for IronOps:** Use `build` (not `build-plugin`) since IronOps does one thing:

```makefile
build:
	@uv run ironops build [--manifest path/to/manifest.json]
```

Prefer invoking via the entry-point once `[project.scripts]` is wired — it tests the install path.

### Pattern 3.3 — Help target

**Source:** `/config/workspace/IronClaude/Makefile:491-523`

Long `@echo` block grouped by category (Quick Start, Development, Plugin Packaging, Documentation, Cleanup).

**Why relevant to IronOps:** `make help` is the discoverability entry point.

**Adapt for IronOps:** Short version — IronOps has maybe 6-8 targets. Skip the category headers unless target count grows past 10.

---

## 4. Click CLI Structure

### Pattern 4.1 — `@click.group()` entry

**Source:** `/config/workspace/IronClaude/src/superclaude/cli/main.py:18-26`

```python
import click
from superclaude import __version__

@click.group()
@click.version_option(version=__version__, prog_name="SuperClaude")
def main():
    """SuperClaude - ..."""
    pass
```

**Why relevant to IronOps:** Standard click pattern for a multi-command CLI. `@click.version_option` automatically adds `--version`.

**Adapt for IronOps:**

```python
import click
from ironops import __version__

@click.group()
@click.version_option(version=__version__, prog_name="IronOps")
def main():
    """IronOps - DevOps Claude Plugin builder."""
    pass
```

For v0.1 with a single command (`build`), still use `@click.group()` so adding `verify`, `clean`, etc. later doesn't require restructuring.

### Pattern 4.2 — Subcommand with options

**Source:** `/config/workspace/IronClaude/src/superclaude/cli/main.py:215-258` (the `mcp` subcommand)

```python
@main.command()
@click.option("--servers", "-s", multiple=True, help="Specific MCP servers to install")
@click.option("--list", "list_only", is_flag=True, help="List available MCP servers")
@click.option("--scope", default="user",
              type=click.Choice(["local", "project", "user"]),
              help="Installation scope")
@click.option("--dry-run", is_flag=True,
              help="Show what would be installed without actually installing")
def mcp(servers, list_only, scope, dry_run):
    if list_only:
        ...
        return
    success, message = install_mcp_servers(...)
    click.echo(message)
    if not success:
        sys.exit(1)
```

**Why relevant to IronOps:** Shows the canonical patterns for `is_flag`, multi-value (`multiple=True`), choices, and `--dry-run` as an `is_flag` boolean.

**Adapt for IronOps:**

```python
@main.command()
@click.option("--manifest", type=click.Path(exists=True, dir_okay=False, path_type=Path),
              required=True, help="Path to manifest JSON file")
@click.option("--source", type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=Path.cwd(), help="Source repository root (default: cwd)")
@click.option("--dest", type=click.Path(file_okay=False, path_type=Path),
              required=True, help="Destination directory for the built plugin")
@click.option("--dry-run", is_flag=True, help="Preview without writing files")
@click.option("--verbose", is_flag=True, help="Verbose logging")
def build(manifest, source, dest, dry_run, verbose):
    """Build a Claude plugin from a manifest allowlist."""
    ...
```

Note `click.Path(path_type=Path)` returns a `pathlib.Path` directly — cleaner than IronClaude's post-conversion `Path(target).expanduser()` at `cli/main.py:162`.

### Pattern 4.3 — Exit-code discipline

**Source:** `/config/workspace/IronClaude/src/superclaude/cli/main.py:211-212, 256-257, 348-349, 389-391`

Pattern: every subcommand explicitly calls `sys.exit(1)` on failure paths; success paths fall through (implicit 0).

**Why relevant to IronOps:** A builder must return nonzero on failure or CI cannot detect it.

**Adapt for IronOps:** Copy this discipline. Each command's failure paths explicit `sys.exit(1)`.

---

## 5. UV Installation in CI

### Pattern 5.1 — Install UV snippet

**Source:** `/config/workspace/IronClaude/.github/workflows/test.yml:28-39`

```yaml
- name: Install UV
  run: |
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "$HOME/.cargo/bin" >> $GITHUB_PATH

- name: Verify UV installation
  run: uv --version

- name: Install dependencies
  run: |
    uv pip install --system -e ".[dev]"
    uv pip list --system
```

**Why relevant to IronOps:** This exact snippet is duplicated across five workflow jobs in IronClaude (`test`, `lint`, `plugin-check`, `verify-deps`, `doctor-check`). Org-blessed UV install vector for GitHub Actions.

**Adapt for IronOps:** Copy verbatim. The `--system` flag installs into the runner's system Python — required because GitHub Actions doesn't create a venv automatically.

---

## 6. Pytest Matrix on Python 3.10/3.11/3.12

### Pattern 6.1 — Matrix declaration

**Source:** `/config/workspace/IronClaude/.github/workflows/test.yml:11-27`

```yaml
jobs:
  test:
    name: Test on Python ${{ matrix.python-version }}
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
```

**Why relevant to IronOps:** Matches `requires-python = ">=3.10"` from pyproject.

**Adapt for IronOps:** Copy verbatim. `fail-fast: false` means a 3.10 failure doesn't kill the 3.11/3.12 runs — important for diagnosing version-specific issues.

### Pattern 6.2 — Coverage on one Python version

**Source:** `/config/workspace/IronClaude/.github/workflows/test.yml:50-62`

```yaml
- name: Run tests with coverage
  if: matrix.python-version == '3.10'
  run: |
    pytest --cov=superclaude --cov-report=xml --cov-report=term

- name: Upload coverage to Codecov
  if: matrix.python-version == '3.10'
  uses: codecov/codecov-action@v4
  with:
    file: ./coverage.xml
    flags: unittests
    name: codecov-umbrella
    fail_ci_if_error: false
```

**Why relevant to IronOps:** Don't run coverage on every matrix cell — wasteful. Pin to lowest version (3.10).

**Adapt for IronOps:**
- Use `--cov=ironops`.
- `fail_ci_if_error: false` (or omit Codecov entirely for v0.1) — coverage uploads shouldn't break CI if Codecov is flaky.

### Pattern 6.3 — Summary aggregation job

**Source:** `/config/workspace/IronClaude/.github/workflows/test.yml:176-205`

```yaml
test-summary:
  name: Test Summary
  runs-on: ubuntu-latest
  needs: [test, lint, plugin-check, doctor-check, verify-deps]
  if: always()
  steps:
    - name: Check test results
      run: |
        if [ "${{ needs.test.result }}" != "success" ]; then
          exit 1
        fi
        ...
```

**Why relevant to IronOps:** Required-checks UI in GitHub branch protection works best with a single aggregator job.

**Adapt for IronOps:** For v0.1 with fewer jobs, this aggregator can be added later. Skip in initial scope.

---

## 7. @dataclass Result Types

### Pattern 7.1 — Result dataclass + to_dict()

**Source:** `/config/workspace/IronClaude/scripts/sync_from_framework.py:47-65`

```python
from dataclasses import asdict, dataclass

@dataclass
class SyncResult:
    success: bool
    timestamp: str
    framework_commit: str
    framework_version: str
    files_synced: int
    files_modified: int
    ...
    warnings: List[str]
    errors: List[str]

    def to_dict(self) -> dict:
        return asdict(self)
```

**Why relevant to IronOps:** A builder run produces a structured result (files copied, files skipped, manifest version, warnings, errors). Returning a dataclass makes the surface testable and JSON-serializable.

**Adapt for IronOps:**

```python
from dataclasses import asdict, dataclass
from typing import List

@dataclass
class BuildResult:
    """Result of a single IronOps build run."""
    success: bool
    timestamp: str
    manifest_path: str
    source_root: str
    dest_root: str
    files_copied: int
    files_skipped: int
    warnings: List[str]
    errors: List[str]

    def to_dict(self) -> dict:
        return asdict(self)
```

The `--output-report` pattern (`sync_from_framework.py:874, 895-897`) is also worth copying:

```python
if args.output_report:
    args.output_report.write_text(json.dumps(result.to_dict(), indent=2) + "\n")
```

---

## 8. subprocess + git Invocation Patterns

### Pattern 8.1 — `git rev-parse` for repo detection

**Source:** `/config/workspace/IronClaude/scripts/sync_from_framework.py:158-172`

```python
def _check_git(self) -> bool:
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=self.plugin_root,
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("Git not available - file operations will not preserve history")
        return False
```

**Why relevant to IronOps:** Builder may want to detect whether source is a git repo (to record commit SHA in the build report).

**Adapt for IronOps:** Copy the shape. Use to populate a `source_commit` field in `BuildResult`. **Not strictly required for v0.1** — defer if scope-pressured.

### Pattern 8.2 — `git rev-parse HEAD` for commit SHA

**Source:** `/config/workspace/IronClaude/scripts/sync_from_framework.py:671-683`

```python
def _get_commit_hash(self, repo_path: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"
```

**Why relevant to IronOps:** Embedding the source commit in the build artefact (e.g., a `BUILD-INFO` file or the manifest's output `plugin.json`) is best practice for reproducibility.

**Adapt for IronOps:** Copy verbatim. Note the consistent `text=True, capture_output=True, check=True` triple — this is the right default for any subprocess that should fail loudly.

### Pattern 8.3 — `git ls-remote` for remote HEAD check

**Source:** `/config/workspace/IronClaude/.github/workflows/pull-sync-framework.yml:22-25`

```bash
FRAMEWORK_HEAD=$(git ls-remote https://github.com/SuperClaude-Org/SuperClaude_Framework HEAD | cut -f1)
echo "framework-head=$FRAMEWORK_HEAD" >> $GITHUB_OUTPUT
```

**Why relevant to IronOps:** Useful pattern for any IronOps scheduled workflow that needs to check "has the source changed since last build" without a full clone.

**Adapt for IronOps:** Only relevant if IronOps adds a scheduled "rebuild on upstream change" workflow. **Out of scope for v0.1** but document for future.

### Pattern 8.4 — `git clone --depth 1` for shallow source fetch

**Source:** `/config/workspace/IronClaude/scripts/sync_from_framework.py:651-663`

```python
subprocess.run(
    ["git", "clone", "--depth", "1", self.framework_repo, str(framework_path)],
    check=True,
    capture_output=True,
    text=True,
)
```

**Why relevant to IronOps:** If IronOps ever needs to fetch source from a remote (rather than always-local), shallow clone is the right choice.

**Adapt for IronOps:** **Defer to post-v0.1.** v0.1 builder operates on a local source tree — keep it that way.

---

## 9. Logging Configuration

### Pattern 9.1 — Module-level logger setup

**Source:** `/config/workspace/IronClaude/scripts/sync_from_framework.py:34-38`

```python
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
```

**Why relevant to IronOps:** Standard, low-ceremony logging setup. The format includes timestamps (useful for build-time debugging).

**Adapt for IronOps:** Copy verbatim. Adjust to DEBUG when `--verbose` is set (see Pattern 9.2).

### Pattern 9.2 — Verbose-flag → DEBUG escalation

**Source:** `/config/workspace/IronClaude/scripts/sync_from_framework.py:879-880`

```python
if args.verbose:
    logging.getLogger().setLevel(logging.DEBUG)
```

**Why relevant to IronOps:** Lets CLI users opt into verbose output with one flag.

**Adapt for IronOps:** Copy verbatim. Wire to the click `--verbose` flag from Pattern 4.2.

---

## 10. --dry-run Flag Implementation Pattern

### Pattern 10.1 — Dry-run logged-but-skipped writes

**Source:** `/config/workspace/IronClaude/scripts/sync_from_framework.py:251-268`

```python
def _git_mv(self, old_path: Path, new_path: Path):
    if self.dry_run:
        logger.info(f"  [DRY RUN] git mv {old_path.name} {new_path.name}")
        return

    try:
        subprocess.run(
            ["git", "mv", str(old_path), str(new_path)],
            cwd=self.plugin_root,
            check=True,
            capture_output=True,
        )
        ...
```

Same shape at `sync_from_framework.py:233-234, 245-246, 293-295, 364-366`:

```python
if not self.dry_run:
    dest_file.write_text(content, encoding="utf-8")
```

**Why relevant to IronOps:** A builder MUST have a dry-run mode for safety. Pattern: check `self.dry_run` immediately before any mutating I/O, log what would happen, return early.

**Adapt for IronOps:**
- Thread `dry_run: bool` through the `PluginBuilder` constructor.
- Guard every `shutil.copy2`, `Path.write_text`, `Path.mkdir`, `shutil.rmtree` call.
- Log `[DRY RUN] would copy <src> → <dest>` consistently.

### Pattern 10.2 — Early dry-run announcement

**Source:** `/config/workspace/IronClaude/scripts/sync_from_framework.py:882-883`

```python
if args.dry_run:
    logger.info("DRY RUN MODE - No changes will be applied")
```

**Why relevant to IronOps:** Tells the user upfront they're in preview mode.

**Adapt for IronOps:** Copy verbatim.

---

## 11. Orchestrator Class Pattern

### Pattern 11.1 — Main orchestrator class shape

**Source:** `/config/workspace/IronClaude/scripts/sync_from_framework.py:436-573`

```python
class FrameworkSyncer:
    """Main orchestrator for Framework → Plugin sync."""

    SYNC_MAPPINGS = {...}
    PROTECTED_PATHS: List[str] = [...]

    def __init__(self, framework_repo: str, plugin_root: Path, dry_run: bool = False):
        self.framework_repo = framework_repo
        self.plugin_root = plugin_root
        self.dry_run = dry_run
        self.warnings = []
        self.errors = []

    def sync(self) -> SyncResult:
        try:
            # Step 1: ...
            # Step 2: ...
            return SyncResult(success=True, ...)
        except SpecificError as e:
            self.errors.append(str(e))
            return SyncResult(success=False, ...)
        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)
            self.errors.append(str(e))
            return SyncResult(success=False, ...)
        finally:
            self._cleanup()
```

**Why relevant to IronOps:** Right shape for IronOps' build orchestrator — numbered steps, accumulated `warnings`/`errors` lists, always-returns-a-Result-object (never raises out of the public method), `finally` block for cleanup.

**Adapt for IronOps:**
- IronOps' equivalent: `class PluginBuilder` with `build() -> BuildResult` public method.
- IronOps has FEWER steps (load manifest → snapshot dest → copy allowlisted files → write metadata → validate).
- **Do not copy the helper class explosion** (`ContentTransformer`, `FileSyncer`, `PluginJsonGenerator`, `McpMerger`). IronOps doesn't transform content; one orchestrator class + small private methods is enough for v0.1.

### Pattern 11.2 — Custom exception type

**Source:** `/config/workspace/IronClaude/scripts/sync_from_framework.py:41-44`

```python
class ProtectionViolationError(RuntimeError):
    """Raised when sync would overwrite a Plugin-owned file listed in PROTECTED_PATHS."""
    pass
```

**Why relevant to IronOps:** Domain-specific errors deserve typed exceptions so callers (and tests) can catch them precisely.

**Adapt for IronOps:** Define `class ManifestValidationError(RuntimeError)`, `class SourceFileMissingError(RuntimeError)` for obvious failure classes.

---

## 12. Scheduled Workflow + workflow_dispatch Trigger Pattern

### Pattern 12.1 — Cron + manual trigger

**Source:** `/config/workspace/IronClaude/.github/workflows/pull-sync-framework.yml:3-7`

```yaml
on:
  schedule:
    - cron: '0 */6 * * *'
  workflow_dispatch:
```

**Why relevant to IronOps:** If IronOps gains a scheduled rebuild capability (e.g., nightly plugin rebuild from a tracked source), this is the standard shape. `workflow_dispatch` adds the manual "Run workflow" button in the Actions UI.

**Adapt for IronOps:** **Not in v0.1 scope.** Document for future.

### Pattern 12.2 — Conditional-on-update workflow steps

**Source:** `/config/workspace/IronClaude/.github/workflows/pull-sync-framework.yml:20-41`

```yaml
- name: Check for Framework updates
  id: check-updates
  run: |
    FRAMEWORK_HEAD=$(git ls-remote ... | cut -f1)
    LAST_SYNCED=""
    if [ -f "plugin-repo/docs/.framework-sync-commit" ]; then
      LAST_SYNCED=$(cat plugin-repo/docs/.framework-sync-commit)
    fi
    if [ "$FRAMEWORK_HEAD" = "$LAST_SYNCED" ] && [ "${{ github.event_name }}" != "workflow_dispatch" ]; then
      echo "has-updates=false" >> $GITHUB_OUTPUT
    else
      echo "has-updates=true" >> $GITHUB_OUTPUT
    fi

- name: Run sync
  if: steps.check-updates.outputs.has-updates == 'true'
  run: ...
```

**Why relevant to IronOps:** Pattern for "skip the expensive work if nothing changed." Note the override: `workflow_dispatch` always forces a run.

**Adapt for IronOps:** **Out of v0.1 scope.** Useful template if IronOps later adds scheduled rebuilds.

---

## 13. Protection-File Verification Pattern

### Pattern 13.1 — git diff for unintended-modification detection

**Source:** `/config/workspace/IronClaude/.github/workflows/pull-sync-framework.yml:62-84`

```bash
PROTECTED=(
  "README.md" "SECURITY.md" "CLAUDE.md" "LICENSE" ".gitignore"
)
VIOLATIONS=()
for path in "${PROTECTED[@]}"; do
  if git diff --name-only HEAD -- "$path" | grep -q .; then
    VIOLATIONS+=("$path")
  fi
done
if [ ${#VIOLATIONS[@]} -gt 0 ]; then
  echo "PROTECTION VIOLATION: sync modified Plugin-owned files:"
  for v in "${VIOLATIONS[@]}"; do echo "  - $v"; done
  exit 1
fi
```

**Why relevant to IronOps:** Defense-in-depth — even if in-process protection logic (hash snapshot in `sync_from_framework.py:577-639`) has a bug, the CI step catches unauthorized writes to specific paths.

**Adapt for IronOps:** IronOps' use case is INVERTED — the builder writes to a DESTINATION, not to the source tree. The relevant protection is: "the manifest must not list files outside the source tree" (path-traversal protection). Implement in code, not in CI.

- v0.1 IronOps protection (in `PluginBuilder.build`):

```python
for relpath in manifest["files"]:
    candidate = (source_root / relpath).resolve()
    if not candidate.is_relative_to(source_root.resolve()):
        raise ManifestValidationError(f"Manifest entry escapes source root: {relpath}")
```

The `git diff --name-only HEAD -- <path>` shell pattern is reusable in CI for IronOps' own self-protection (e.g., "the builder should never modify the IronOps repo itself when run from CI on a sample manifest").

### Pattern 13.2 — Hash-snapshot in-process protection

**Source:** `/config/workspace/IronClaude/scripts/sync_from_framework.py:577-639`

```python
@staticmethod
def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()

def _snapshot_protected_files(self) -> Dict[str, str]:
    snapshot: Dict[str, str] = {}
    for protected in self.PROTECTED_PATHS:
        target = self.plugin_root / protected
        if target.is_file():
            snapshot[protected] = self._hash_file(target)
        elif target.is_dir():
            for f in sorted(target.rglob("*")):
                if f.is_file():
                    rel = str(f.relative_to(self.plugin_root))
                    snapshot[rel] = self._hash_file(f)
    return snapshot

def _validate_protected_files(self, snapshot: Dict[str, str]) -> None:
    violations: List[str] = []
    for rel_path, original_hash in snapshot.items():
        current = self.plugin_root / rel_path
        if not current.exists():
            violations.append(f"DELETED  : {rel_path}")
        else:
            if self._hash_file(current) != original_hash:
                violations.append(f"MODIFIED : {rel_path}")
    if violations:
        raise ProtectionViolationError(...)
```

**Why relevant to IronOps:** IronOps' byte-identical-copy guarantee can be verified with a similar approach — hash every source file before-and-after the build, hash every dest file post-build, assert source unchanged AND dest matches source for every manifest entry.

**Adapt for IronOps:**
- Use SHA-256 (already chosen in IronClaude — consistent).
- Replace `read_bytes()` with chunked read for large binary files (not needed for v0.1 if plugins are small).
- Skip the snapshot of SOURCE files for v0.1 — the in-process invariant is simpler: never `open(src, "w")`, never `Path(src).unlink()`, never `shutil.rmtree(source_root)`. Code review enforces this.
- DO use post-build hash equality between source and dest as the byte-identical verification:

```python
for relpath in manifest["files"]:
    src_hash = sha256_of(source_root / relpath)
    dst_hash = sha256_of(dest_root / relpath)
    if src_hash != dst_hash:
        errors.append(f"BYTE_DRIFT: {relpath}")
```

---

## 14. Argparse vs Click

**Observation:** `sync_from_framework.py:854-877` uses argparse; `cli/main.py` uses click. IronClaude's convention is **click for CLI entry points, argparse only for one-off scripts**.

**Adapt for IronOps:** Use click throughout. The build orchestrator should be reachable via `ironops build` (click), not `python scripts/build.py` (argparse). The IronClaude script-vs-entry-point split is a historical artifact, not something to copy.

---

## Adaptation Summary for IronOps

The 12 most important patterns to apply, ranked by impact:

1. **`src/ironops/` layout + hatchling pyproject.toml** (Patterns 1.1, 2.1, 2.3) — copy IronClaude's pyproject shape minus pytest-plugin entry-point and minus `force-include` hack.
2. **Click `@click.group()` + per-command modules** (Patterns 4.1, 4.2) — `ironops build --manifest ... --source ... --dest ... --dry-run --verbose`. Use `click.Path(path_type=Path)` for path options. Exit nonzero on failure (Pattern 4.3).
3. **PluginBuilder orchestrator class with `build() -> BuildResult`** (Pattern 11.1) — single class, numbered steps in the `try`, accumulated `warnings`/`errors` lists, `finally` cleanup, never raises out of public method.
4. **`@dataclass BuildResult` with `to_dict()` + `--output-report path.json`** (Pattern 7.1) — testable, JSON-serializable result surface.
5. **Logging setup + `--verbose` → DEBUG** (Patterns 9.1, 9.2) — `logging.basicConfig(level=INFO, format="%(asctime)s - %(levelname)s - %(message)s")`; verbose flips to DEBUG.
6. **Dry-run discipline — guard every mutating I/O call** (Patterns 10.1, 10.2) — `if not self.dry_run:` before `write_text`, `copy2`, `mkdir`, `rmtree`; log `[DRY RUN]` what would happen; announce mode at start.
7. **Custom exception types** (Pattern 11.2) — `ManifestValidationError`, `SourceFileMissingError`, `ByteDriftError` so tests can catch specifically.
8. **Hash-based byte-identical verification** (Pattern 13.2, adapted) — SHA-256 of source file == SHA-256 of dest file for every manifest entry; populates `BuildResult.errors` as `BYTE_DRIFT: <path>`.
9. **Path-traversal validation on manifest entries** (Pattern 13.1, adapted) — `(source_root / relpath).resolve().is_relative_to(source_root.resolve())`.
10. **subprocess `git rev-parse HEAD` for source commit** (Pattern 8.2) — optional but cheap; embed in `BuildResult.source_commit` for traceability.
11. **Makefile with org-standard targets** (Patterns 3.1, 3.2) — `install`, `test`, `lint`, `format`, `clean`, `build`, `help`. `uv run` everywhere.
12. **CI: UV install snippet + pytest matrix 3.10/3.11/3.12 + coverage on 3.10 only** (Patterns 5.1, 6.1, 6.2) — verbatim from `test.yml`, dropping the pytest-plugin-loaded check and dependency-allowlist job.

### Explicit non-copies (anti-patterns or out-of-scope for v0.1)

- **Do not copy `build_superclaude_plugin.py`** — references nonexistent `MANIFEST_DIR = PLUGIN_SRC / "manifest"` (`scripts/build_superclaude_plugin.py:18`); it's broken and template-driven (a separate problem class).
- **Do not copy `sync_from_framework.py`'s `ContentTransformer`** — IronOps does byte-identical copy, no rewriting.
- **Do not copy the helper-class explosion** (`FileSyncer`, `PluginJsonGenerator`, `McpMerger`). One orchestrator class is enough.
- **Do not adopt argparse** — use click everywhere (Section 14).
- **Defer scheduled-workflow / `workflow_dispatch` / `git ls-remote`** — not v0.1 scope.
- **Defer `git clone --depth 1`** — v0.1 builder operates on local source tree.
- **Defer `flake8-tidy-imports.banned-api`** — that's a SuperClaude-specific anthropic-SDK ban.
- **Skip `force-include` hack in hatchling** — SuperClaude needs it to ship sources at runtime; IronOps does not.
- **Skip `pexpect`, `pyyaml`, `jsonschema` deps** — not needed for a JSON-manifest byte-copy builder.

---

## Status: Complete

## Summary

Researched 8 IronClaude source files and extracted 30+ concrete patterns across 14 categories spanning project layout, pyproject.toml shape, Makefile targets, click CLI structure, UV CI install, pytest matrix, dataclass result types, subprocess+git invocation, logging, --dry-run discipline, orchestrator class shape, scheduled-workflow shape, and protection-file verification. Every pattern is cited with `file:line` references against the IronClaude tree.

The "Adaptation Summary for IronOps" section identifies the 12 highest-impact patterns to apply for the v0.1 builder, and explicitly enumerates anti-patterns / out-of-scope items to avoid (broken `build_superclaude_plugin.py`, the `ContentTransformer` rewriting logic, the helper-class explosion, argparse, scheduled-workflow machinery).

Key insight: IronOps' v0.1 surface is FAR smaller than IronClaude's tooling (one command, byte-identical copy, manifest allowlist). The adaptation discipline is therefore aggressive subtraction — copy the SHAPE of IronClaude's `pyproject.toml`, click CLI, Makefile, orchestrator class, dry-run threading, and dataclass result — drop everything specific to SuperClaude's multi-component, content-rewriting, pytest-plugin nature.

