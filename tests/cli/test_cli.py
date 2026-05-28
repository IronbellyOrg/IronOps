"""CLI tests using click.testing.CliRunner."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from ironops.cli import cli

EXPECTED_TOP_LEVEL_COMMANDS = frozenset({"build", "validate", "version"})
FIXTURES = Path(__file__).parent.parent / "fixtures" / "manifests"


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_help_lists_all_commands(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0, result.output
    for cmd in EXPECTED_TOP_LEVEL_COMMANDS:
        assert cmd in result.output


def test_cli_version_prints_version_and_sha(runner):
    result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0, result.output
    assert "IronOps" in result.output
    assert "0.1.0" in result.output


def test_cli_build_help_exposes_flags(runner):
    result = runner.invoke(cli, ["build", "--help"])
    assert result.exit_code == 0, result.output
    for flag in ["--manifest", "--staging", "--marketplace", "--dry-run", "--verbose"]:
        assert flag in result.output
    # D5 — NO --allow-dirty flag
    assert "--allow-dirty" not in result.output


def test_cli_build_bad_manifest_exits_with_categorical_code(
    runner, tmp_path, ironclaude_fixture_repo, mock_git_clone, mock_claude_validate, patched_builder_version,
):
    """bad-schema.yaml manifest yields exit code MANIFEST_INVALID=10."""
    yml = (FIXTURES / "bad-schema.yaml").read_text()
    manifest_path = tmp_path / "bad.yaml"
    manifest_path.write_text(yml)
    result = runner.invoke(cli, [
        "build", "--manifest", str(manifest_path),
        "--staging", str(tmp_path / "staging"),
        "--scratch", str(tmp_path / "scratch"),
        "--dry-run",
    ], input="")
    assert result.exit_code == 10  # MANIFEST_INVALID
    assert "MANIFEST_INVALID" in result.output


def test_cli_build_dry_run_happy_path(
    runner, tmp_path, ironclaude_fixture_repo, mock_git_clone, mock_claude_validate, patched_builder_version,
):
    """Good manifest + dry-run exits 0."""
    yml = (FIXTURES / "good.yaml").read_text().replace(
        "{{IRONCLAUDE_SNAPSHOT_PATH}}", str(ironclaude_fixture_repo)
    )
    manifest_path = tmp_path / "good.yaml"
    manifest_path.write_text(yml)
    result = runner.invoke(cli, [
        "build", "--manifest", str(manifest_path),
        "--staging", str(tmp_path / "staging"),
        "--scratch", str(tmp_path / "scratch"),
        "--dry-run",
    ], input="")
    assert result.exit_code == 0, result.output


def test_cli_no_interactive_input_required(
    runner, tmp_path, ironclaude_fixture_repo, mock_git_clone, mock_claude_validate, patched_builder_version,
):
    """FR-12-A2 — CLI never prompts for input."""
    yml = (FIXTURES / "good.yaml").read_text().replace(
        "{{IRONCLAUDE_SNAPSHOT_PATH}}", str(ironclaude_fixture_repo)
    )
    manifest_path = tmp_path / "good.yaml"
    manifest_path.write_text(yml)
    # input="" simulates no stdin available
    result = runner.invoke(cli, [
        "build", "--manifest", str(manifest_path),
        "--staging", str(tmp_path / "staging"),
        "--scratch", str(tmp_path / "scratch"),
        "--dry-run",
    ], input="")
    # Build should complete without consuming stdin
    assert result.exit_code in (0, 10, 11, 12, 13, 14, 15, 16, 17, 18), result.output
