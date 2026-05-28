"""AC-10 — every malformed-manifest fixture fails fast with the correct exit code."""

from __future__ import annotations

from pathlib import Path

import pytest

from ironops.errors import ExitCode
from ironops.pipeline import BuildContext, run_build

FIXTURES = Path(__file__).parent.parent / "fixtures" / "manifests"


@pytest.mark.parametrize(
    "fixture_name,expected_code",
    [
        ("bad-schema.yaml", ExitCode.MANIFEST_INVALID),
        ("bad-empty-imports.yaml", ExitCode.MANIFEST_INVALID),
        ("bad-self-overwrite.yaml", ExitCode.SELF_OVERWRITE),
        ("bad-path-escape.yaml", ExitCode.PATH_ESCAPE),
        ("bad-hook-kind.yaml", ExitCode.MANIFEST_INVALID),
    ],
    ids=["bad-schema", "bad-empty-imports", "bad-self-overwrite", "bad-path-escape", "bad-hook-kind"],
)
def test_bad_manifest_fails_with_categorical_code(
    tmp_path, ironclaude_fixture_repo, mock_git_clone, mock_claude_validate,
    patched_builder_version, fixture_name, expected_code,
):
    """Each bad-*.yaml fixture must fail with the documented categorical ExitCode."""
    yml = (FIXTURES / fixture_name).read_text().replace(
        "{{IRONCLAUDE_SNAPSHOT_PATH}}", str(ironclaude_fixture_repo)
    )
    manifest_path = tmp_path / fixture_name
    manifest_path.write_text(yml)
    ctx = BuildContext(
        manifest_path=manifest_path,
        staging_dir=tmp_path / "staging",
        scratch_dir=tmp_path / "scratch",
        dry_run=True,
    )
    result = run_build(ctx)
    assert not result.success
    assert result.exit_code == expected_code, f"{fixture_name}: expected {expected_code.name}, got {result.exit_code.name}"


def test_orphan_command_fails_with_co_import_missing(
    tmp_path, ironclaude_fixture_repo, mock_git_clone, mock_claude_validate,
    patched_builder_version,
):
    """bad-orphan-command.yaml — command refs Skill sc:troubleshoot-protocol without importing the skill."""
    yml = (FIXTURES / "bad-orphan-command.yaml").read_text().replace(
        "{{IRONCLAUDE_SNAPSHOT_PATH}}", str(ironclaude_fixture_repo)
    )
    manifest_path = tmp_path / "bad-orphan.yaml"
    manifest_path.write_text(yml)
    ctx = BuildContext(
        manifest_path=manifest_path,
        staging_dir=tmp_path / "staging",
        scratch_dir=tmp_path / "scratch",
        dry_run=True,
    )
    result = run_build(ctx)
    assert not result.success
    assert result.exit_code == ExitCode.CO_IMPORT_MISSING


def test_failure_emits_one_line_stderr_summary(
    tmp_path, ironclaude_fixture_repo, mock_git_clone, mock_claude_validate,
    patched_builder_version,
):
    """NFR-7 part (a) — failure summary is exactly one line including the code name."""
    yml = (FIXTURES / "bad-schema.yaml").read_text()
    manifest_path = tmp_path / "bad.yaml"
    manifest_path.write_text(yml)
    ctx = BuildContext(
        manifest_path=manifest_path,
        staging_dir=tmp_path / "staging",
        scratch_dir=tmp_path / "scratch",
        dry_run=True,
    )
    result = run_build(ctx)
    assert not result.success
    assert "\n" not in result.summary
    assert "MANIFEST_INVALID" in result.summary
