"""End-to-end pipeline tests using the hermetic ironclaude-snapshot fixture."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from ironops.errors import ExitCode
from ironops.pipeline import BuildContext, run_build


def _make_manifest(tmp_path: Path, fixture_repo: Path) -> Path:
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

  - source: ironclaude
    from: "src/superclaude/skills/sc-troubleshoot-protocol/"
    to: "skills/sc-troubleshoot-protocol/"
    kind: skill

  - source: ironclaude
    from: "src/superclaude/commands/troubleshoot.md"
    to: "commands/troubleshoot.md"
    kind: command
    requires:
      - "skills/sc-troubleshoot-protocol/"

plugin:
  name: "ironops-devops"
  description: "DevOps plugin"

marketplace:
  name: "ironops"
  owner:
    name: "IronbellyOrg"
"""
    p = tmp_path / "manifest.yaml"
    p.write_text(yml)
    return p


def test_pipeline_dry_run_happy_path(
    tmp_path,
    ironclaude_fixture_repo,
    mock_git_clone,
    mock_claude_validate,
    patched_builder_version,
):
    """Full pipeline dry-run against the hermetic snapshot exits SUCCESS."""
    manifest_path = _make_manifest(tmp_path, ironclaude_fixture_repo)
    ctx = BuildContext(
        manifest_path=manifest_path,
        staging_dir=tmp_path / "staging",
        scratch_dir=tmp_path / "scratch",
        dry_run=True,
        verbose=False,
    )
    result = run_build(ctx)
    assert result.success, f"build failed: {result.summary}"
    assert result.exit_code == ExitCode.SUCCESS


def test_pipeline_emits_all_four_generated_files(
    tmp_path,
    ironclaude_fixture_repo,
    mock_git_clone,
    mock_claude_validate,
    patched_builder_version,
):
    manifest_path = _make_manifest(tmp_path, ironclaude_fixture_repo)
    staging = tmp_path / "staging"
    ctx = BuildContext(
        manifest_path=manifest_path,
        staging_dir=staging,
        scratch_dir=tmp_path / "scratch",
        dry_run=True,
    )
    result = run_build(ctx)
    assert result.success
    assert (staging / ".claude-plugin" / "plugin.json").exists()
    assert (staging / "META.json").exists()
    assert (staging / "THIRD_PARTY_LICENSES.md").exists()
    assert (staging / ".claude-plugin" / "marketplace.json").exists()


def test_pipeline_validator_failure_aborts_publish(
    tmp_path,
    ironclaude_fixture_repo,
    mock_git_clone,
    mock_claude_validate,
    tmp_marketplace_repo,
    patched_builder_version,
):
    """When validator fails, publish stage is never reached."""
    manifest_path = _make_manifest(tmp_path, ironclaude_fixture_repo)
    mock_claude_validate.exit_code = 2  # force validator failure

    pre_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=tmp_marketplace_repo, text=True
    ).strip()
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
    # FR-9 — marketplace HEAD unchanged
    post_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=tmp_marketplace_repo, text=True
    ).strip()
    assert pre_head == post_head


def test_pipeline_publish_message_format(
    tmp_path,
    ironclaude_fixture_repo,
    mock_git_clone,
    mock_claude_validate,
    patched_builder_version,
):
    """AC-6 — commit message includes builder_version + at least one source SHA.

    Tests `_build_commit_message` directly because rsync (required by the
    real publish path) may not be installed in this test environment.
    """
    from ironops.publish import _build_commit_message

    manifest_path = _make_manifest(tmp_path, ironclaude_fixture_repo)
    ctx = BuildContext(
        manifest_path=manifest_path,
        staging_dir=tmp_path / "staging",
        scratch_dir=tmp_path / "scratch",
        dry_run=True,
    )
    result = run_build(ctx)
    assert result.success, f"build failed: {result.summary}"
    assert result.manifest is not None and result.clones
    msg = _build_commit_message(result.manifest, result.clones, patched_builder_version)
    assert patched_builder_version in msg
    # at least one source SHA present
    assert re.search(r"@[0-9a-f]{40}", msg)


def test_pipeline_stage_timing_recorded(
    tmp_path,
    ironclaude_fixture_repo,
    mock_git_clone,
    mock_claude_validate,
    patched_builder_version,
):
    manifest_path = _make_manifest(tmp_path, ironclaude_fixture_repo)
    ctx = BuildContext(
        manifest_path=manifest_path,
        staging_dir=tmp_path / "staging",
        scratch_dir=tmp_path / "scratch",
        dry_run=True,
    )
    result = run_build(ctx)
    assert result.duration_s >= 0
    assert result.duration_s < 60  # well under NFR-2 soft-warn


def test_pipeline_deterministic_excluding_built_at(
    tmp_path,
    ironclaude_fixture_repo,
    mock_git_clone,
    mock_claude_validate,
    patched_builder_version,
):
    """NFR-1 — back-to-back builds produce identical files except META.json.built_at."""
    manifest_path = _make_manifest(tmp_path, ironclaude_fixture_repo)
    staging1 = tmp_path / "staging1"
    staging2 = tmp_path / "staging2"
    for staging in (staging1, staging2):
        ctx = BuildContext(
            manifest_path=manifest_path,
            staging_dir=staging,
            scratch_dir=tmp_path / f"scratch-{staging.name}",
            dry_run=True,
        )
        result = run_build(ctx)
        assert result.success, result.summary

    # compare all files except META.json
    files1 = sorted(p.relative_to(staging1) for p in staging1.rglob("*") if p.is_file())
    files2 = sorted(p.relative_to(staging2) for p in staging2.rglob("*") if p.is_file())
    assert files1 == files2
    for rel in files1:
        f1, f2 = staging1 / rel, staging2 / rel
        if rel.name == "META.json":
            d1 = json.loads(f1.read_text())
            d2 = json.loads(f2.read_text())
            d1.pop("built_at")
            d2.pop("built_at")
            assert d1 == d2
        else:
            assert f1.read_bytes() == f2.read_bytes(), f"diff in {rel}"
