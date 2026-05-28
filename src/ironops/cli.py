"""Flat click CLI group (disposition D2 — NO subpackage).

Subcommands: ``build``, ``validate``, ``version``. NO ``--allow-dirty``
flag (disposition D5 — FR-12 hard-fail). NO ``click.prompt`` (FR-12-A2
deterministic headless).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click

from ironops import __version__
from ironops.errors import ExitCode
from ironops.pipeline import BuildContext, run_build
from ironops.validate import run_validator


@click.group()
@click.version_option(version=__version__, prog_name="IronOps")
def cli() -> None:
    """IronOps DevOps Claude Plugin builder."""


@cli.command()
@click.option(
    "--manifest",
    "manifest_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to the YAML manifest.",
)
@click.option(
    "--staging",
    "staging_dir",
    required=True,
    type=click.Path(path_type=Path),
    help="Output staging directory.",
)
@click.option(
    "--marketplace",
    "marketplace_repo",
    default=None,
    type=click.Path(path_type=Path),
    help="Marketplace repo clone (omit for dry-run-only builds).",
)
@click.option(
    "--scratch",
    "scratch_dir",
    default=None,
    type=click.Path(path_type=Path),
    help="Scratch directory for upstream clones (default: <staging>/../scratch).",
)
@click.option("--dry-run", is_flag=True, help="Skip the publish stage.")
@click.option("--verbose", is_flag=True, help="Verbose stage logging to stderr.")
def build(
    manifest_path: Path,
    staging_dir: Path,
    marketplace_repo: Path | None,
    scratch_dir: Path | None,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Run the 8-stage build pipeline."""
    if scratch_dir is None:
        scratch_dir = staging_dir.parent / "scratch"
    ctx = BuildContext(
        manifest_path=manifest_path,
        staging_dir=staging_dir,
        scratch_dir=scratch_dir,
        marketplace_repo=marketplace_repo,
        dry_run=dry_run,
        verbose=verbose,
    )
    result = run_build(ctx)
    if result.success:
        click.echo(result.summary)
        sys.exit(int(ExitCode.SUCCESS))
    else:
        click.echo(result.summary, err=True)
        sys.exit(int(result.exit_code))


@cli.command("validate")
@click.option(
    "--plugin-dir",
    "plugin_dir",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Plugin staging directory to validate.",
)
def validate_cmd(plugin_dir: Path) -> None:
    """Run ``claude plugin validate`` against an existing plugin tree."""
    try:
        result = run_validator(plugin_dir)
        click.echo(f"validate ok: exit={result.exit_code} duration={result.duration_s:.2f}s")
        sys.exit(int(ExitCode.SUCCESS))
    except Exception as exc:
        click.echo(f"[VALIDATE_FAILED] {exc}", err=True)
        sys.exit(int(ExitCode.VALIDATE_FAILED))


@cli.command()
def version() -> None:
    """Print the builder version and git SHA."""
    sha = "unknown"
    try:
        proc = subprocess.run(
            ["git", "-C", str(Path(__file__).resolve().parents[2]),
             "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5, check=False,
        )
        if proc.returncode == 0:
            sha = proc.stdout.strip()[:12]
    except Exception:
        pass
    click.echo(f"IronOps {__version__} ({sha})")


def main() -> None:
    """Entry point registered in pyproject.toml [project.scripts]."""
    cli()


if __name__ == "__main__":  # pragma: no cover
    main()
