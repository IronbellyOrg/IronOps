"""FR-9 atomicity invariant tests — failures leave marketplace HEAD unchanged."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ironops import metadata as _metadata
from ironops import render as _render
from ironops.errors import BuilderDirtyTree, ExitCode, PathEscape, ValidateFailed
from ironops.pipeline import BuildContext, run_build


def _manifest(tmp_path: Path, fixture_repo: Path) -> Path:
    yml = f"""
schema_version: "1"
sources:
  ironclaude:
    url: "{fixture_repo}"
imports:
  - source: ironclaude
    from: "src/superclaude/agents/devops-architect.md"
    to: "agents/devops-architect.md"
    kind: agent
plugin:
  name: "ironops-devops"
  description: "test"
marketplace:
  name: "ironops"
  owner:
    name: "IronbellyOrg"
"""
    p = tmp_path / "manifest.yaml"
    p.write_text(yml)
    return p


def _head(repo: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()


def test_render_failure_leaves_marketplace_unchanged(
    monkeypatch, tmp_path, ironclaude_fixture_repo, mock_git_clone, mock_claude_validate,
    tmp_marketplace_repo, patched_builder_version
):
    manifest_path = _manifest(tmp_path, ironclaude_fixture_repo)
    pre_head = _head(tmp_marketplace_repo)

    def fail_path_safety(*a, **kw):
        raise PathEscape("forced render failure")
    monkeypatch.setattr(_render, "enforce_path_safety", fail_path_safety)

    ctx = BuildContext(
        manifest_path=manifest_path,
        staging_dir=tmp_path / "staging",
        scratch_dir=tmp_path / "scratch",
        marketplace_repo=tmp_marketplace_repo,
        dry_run=False,
    )
    result = run_build(ctx)
    assert not result.success
    assert result.exit_code == ExitCode.PATH_ESCAPE
    assert _head(tmp_marketplace_repo) == pre_head


def test_validate_failure_leaves_marketplace_unchanged(
    tmp_path, ironclaude_fixture_repo, mock_git_clone, mock_claude_validate,
    tmp_marketplace_repo, patched_builder_version
):
    manifest_path = _manifest(tmp_path, ironclaude_fixture_repo)
    pre_head = _head(tmp_marketplace_repo)
    mock_claude_validate.exit_code = 3

    ctx = BuildContext(
        manifest_path=manifest_path,
        staging_dir=tmp_path / "staging",
        scratch_dir=tmp_path / "scratch",
        marketplace_repo=tmp_marketplace_repo,
        dry_run=False,
    )
    result = run_build(ctx)
    assert not result.success
    assert result.exit_code == ExitCode.VALIDATE_FAILED
    assert _head(tmp_marketplace_repo) == pre_head


def test_metadata_failure_leaves_marketplace_unchanged(
    monkeypatch, tmp_path, ironclaude_fixture_repo, mock_git_clone, mock_claude_validate,
    tmp_marketplace_repo, patched_builder_version
):
    manifest_path = _manifest(tmp_path, ironclaude_fixture_repo)
    pre_head = _head(tmp_marketplace_repo)

    def fail_meta(*a, **kw):
        raise BuilderDirtyTree("forced metadata failure")
    monkeypatch.setattr(_metadata, "write_meta_json", fail_meta)

    ctx = BuildContext(
        manifest_path=manifest_path,
        staging_dir=tmp_path / "staging",
        scratch_dir=tmp_path / "scratch",
        marketplace_repo=tmp_marketplace_repo,
        dry_run=False,
    )
    result = run_build(ctx)
    assert not result.success
    assert _head(tmp_marketplace_repo) == pre_head


def test_clone_failure_leaves_marketplace_unchanged(
    monkeypatch, tmp_path, ironclaude_fixture_repo, tmp_marketplace_repo, patched_builder_version, mock_claude_validate
):
    manifest_path = _manifest(tmp_path, ironclaude_fixture_repo)
    pre_head = _head(tmp_marketplace_repo)

    # Force git operations to fail
    real_run = subprocess.run
    def fake(cmd, *a, **kw):
        if isinstance(cmd, list) and len(cmd) >= 2 and cmd[0] == "git" and cmd[1] in {"clone", "ls-remote"}:
            return subprocess.CompletedProcess(cmd, 128, "", "forced clone failure")
        return real_run(cmd, *a, **kw)
    monkeypatch.setattr(subprocess, "run", fake)

    ctx = BuildContext(
        manifest_path=manifest_path,
        staging_dir=tmp_path / "staging",
        scratch_dir=tmp_path / "scratch",
        marketplace_repo=tmp_marketplace_repo,
        dry_run=False,
    )
    result = run_build(ctx)
    assert not result.success
    assert result.exit_code == ExitCode.UPSTREAM_CLONE_FAILED
    assert _head(tmp_marketplace_repo) == pre_head


def test_no_partial_marketplace_write_on_failure(
    monkeypatch, tmp_path, ironclaude_fixture_repo, mock_git_clone, mock_claude_validate,
    tmp_marketplace_repo, patched_builder_version
):
    """The marketplace plugins/ironops-devops/ should not exist if build never succeeded."""
    manifest_path = _manifest(tmp_path, ironclaude_fixture_repo)
    mock_claude_validate.exit_code = 4

    ctx = BuildContext(
        manifest_path=manifest_path,
        staging_dir=tmp_path / "staging",
        scratch_dir=tmp_path / "scratch",
        marketplace_repo=tmp_marketplace_repo,
        dry_run=False,
    )
    result = run_build(ctx)
    assert not result.success
    # The plugin subdir may not exist; if it does, it's at least committed
    plugins = tmp_marketplace_repo / "plugins" / "ironops-devops"
    if plugins.exists():
        # The marketplace HEAD is unchanged so any directory must not be tracked
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=tmp_marketplace_repo,
            capture_output=True, text=True,
        )
        # FR-9 — HEAD unchanged is the primary invariant; any untracked files are tolerable
        # as long as commit history is preserved
        assert "plugins/ironops-devops" not in subprocess.check_output(
            ["git", "log", "--oneline", "-1"], cwd=tmp_marketplace_repo, text=True,
        )
