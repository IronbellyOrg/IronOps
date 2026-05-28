"""Shared pytest fixtures for IronOps test suite.

Fixtures:
- `tmp_staging` / `tmp_scratch` / `tmp_marketplace_repo` — per-function temp dirs
- `ironclaude_snapshot_path` (session) — read-only path to the hermetic fixture
- `ironclaude_fixture_repo` (session) — git-initialized snapshot for clone tests
- `good_manifest` — copies tests/fixtures/manifests/good.yaml with substitution
- `mock_git_clone` — monkeypatches subprocess.run for git clone/ls-remote
- `mock_claude_validate` — controls validator return code
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Iterator

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SNAPSHOT_DIR = FIXTURES_DIR / "ironclaude-snapshot"
MANIFESTS_DIR = FIXTURES_DIR / "manifests"


@pytest.fixture(autouse=True)
def _redirect_ironops_env(monkeypatch, tmp_path):
    """Auto-redirect any IRONOPS_*_DIR env var to a per-test tmp dir."""
    for key in list(__import__("os").environ.keys()):
        if key.startswith("IRONOPS_") and key.endswith("_DIR"):
            monkeypatch.setenv(key, str(tmp_path / key.lower()))


@pytest.fixture
def tmp_staging(tmp_path: Path) -> Path:
    p = tmp_path / "staging"
    p.mkdir()
    return p


@pytest.fixture
def tmp_scratch(tmp_path: Path) -> Path:
    p = tmp_path / "scratch"
    p.mkdir()
    return p


@pytest.fixture
def tmp_marketplace_repo(tmp_path: Path) -> Path:
    """A real git repo with one initial commit so push targets work."""
    repo = tmp_path / "marketplace"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@ironops.local"], cwd=repo, check=True
    )
    subprocess.run(["git", "config", "user.name", "IronOps Test"], cwd=repo, check=True)
    (repo / "README.md").write_text("# marketplace\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True
    )
    return repo


@pytest.fixture(scope="session")
def ironclaude_snapshot_path() -> Path:
    """Read-only path to the hermetic IronClaude fixture."""
    return SNAPSHOT_DIR


@pytest.fixture(scope="session")
def ironclaude_fixture_repo(tmp_path_factory, ironclaude_snapshot_path: Path) -> Path:
    """A real git repo cloned from the snapshot, with an initial commit."""
    repo = tmp_path_factory.mktemp("ironclaude_fixture")
    # Copy snapshot src/ tree
    src_root = ironclaude_snapshot_path / "src"
    if src_root.exists():
        shutil.copytree(src_root, repo / "src")
    license_src = ironclaude_snapshot_path / "LICENSE"
    if license_src.exists():
        shutil.copy2(license_src, repo / "LICENSE")
    subprocess.run(
        ["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@ironops.local"], cwd=repo, check=True
    )
    subprocess.run(["git", "config", "user.name", "IronOps Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "snapshot"], cwd=repo, check=True, capture_output=True
    )
    return repo


@pytest.fixture
def good_manifest(tmp_path: Path, ironclaude_fixture_repo: Path) -> Path:
    """A copy of fixtures/manifests/good.yaml with the snapshot path interpolated."""
    src = MANIFESTS_DIR / "good.yaml"
    text = src.read_text()
    # The fixture URL points at the local fixture repo so clone tests can run hermetic
    text = text.replace("{{IRONCLAUDE_SNAPSHOT_PATH}}", str(ironclaude_fixture_repo))
    dst = tmp_path / "good.yaml"
    dst.write_text(text)
    return dst


@pytest.fixture
def mock_git_clone(monkeypatch, ironclaude_fixture_repo: Path):
    """Replace subprocess.run for git clone/ls-remote calls.

    Returns a controller object whose .behavior attribute can be set to:
      - "ok"  : pretend ls-remote succeeds and clone copies from the fixture
      - "fail-ls-remote"
      - "fail-clone"
    """
    real_run = subprocess.run
    controller = type("ctrl", (), {"behavior": "ok"})()

    def fake_run(cmd, *args, **kwargs):
        if isinstance(cmd, list) and len(cmd) >= 2 and cmd[0] == "git":
            sub = cmd[1]
            if sub == "ls-remote":
                if controller.behavior == "fail-ls-remote":
                    return subprocess.CompletedProcess(cmd, 128, "", "ls-remote error")
                return subprocess.CompletedProcess(
                    cmd,
                    0,
                    "ref: refs/heads/main\tHEAD\nabc123\tHEAD\n",
                    "",
                )
            if sub == "clone":
                if controller.behavior == "fail-clone":
                    return subprocess.CompletedProcess(cmd, 128, "", "clone error")
                # Find dest (last positional arg)
                dest = Path(cmd[-1])
                shutil.copytree(ironclaude_fixture_repo, dest)
                return subprocess.CompletedProcess(cmd, 0, "", "")
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)
    return controller


@pytest.fixture
def mock_claude_validate(monkeypatch):
    """Make validate.run_validator return a successful result without invoking claude CLI."""
    from ironops import validate as _v

    controller = type("ctrl", (), {"exit_code": 0, "stdout": "ok", "stderr": ""})()

    def fake_run_validator(staging_dir, log_dir=None) -> _v.ValidatorResult:
        if controller.exit_code != 0:
            from ironops.errors import ValidateFailed

            raise ValidateFailed(
                f"mocked validator failure exit={controller.exit_code}"
            )
        if (
            "warning" in controller.stdout.lower()
            or "warning" in controller.stderr.lower()
        ):
            from ironops.errors import ValidateFailed

            raise ValidateFailed("mocked validator warning")
        return _v.ValidatorResult(
            exit_code=controller.exit_code,
            stdout=controller.stdout,
            stderr=controller.stderr,
            duration_s=0.01,
        )

    monkeypatch.setattr(_v, "run_validator", fake_run_validator)
    return controller


@pytest.fixture
def patched_builder_version(monkeypatch) -> Iterator[str]:
    """Force metadata._resolve_builder_version to return a deterministic SHA."""
    sha = "0" * 40
    from ironops import metadata

    monkeypatch.setattr(metadata, "_resolve_builder_version", lambda *a, **k: sha)
    yield sha
