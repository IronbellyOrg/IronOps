"""Atomic publish via rsync + git add/commit/push.

Implements FR-9 (atomic publish; failure leaves marketplace HEAD
unchanged), FR-10 (marketplace.json fanout), AC-6 (commit message
contains builder_version + at least one source SHA), NFR-6
(auditability).
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ironops.errors import PublishFailed
from ironops.manifest import Manifest
from ironops.sources import ClonedSource

MARKETPLACE_PLUGIN_SUBDIR: str = "plugins/ironops-devops"
DEFAULT_RSYNC_FLAGS: list[str] = ["-a", "--delete"]


@dataclass(frozen=True)
class PublishResult:
    pushed: bool
    commit_sha: str | None
    commit_message: str


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


def _get_default_branch(marketplace_repo: Path) -> str:
    """Return the marketplace repo's current branch (HEAD symbolic ref)."""
    proc = _run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=marketplace_repo
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise PublishFailed(
            f"could not resolve marketplace branch: {proc.stderr.strip()}"
        )
    return proc.stdout.strip()


def _rsync_staging(staging: Path, marketplace_plugin_dir: Path) -> None:
    """Mirror staging tree into the marketplace plugin subdir.

    Uses explicit trailing slashes on the source (B.7) so rsync copies
    *contents* (not the staging directory itself). ``--delete`` enforces
    mirror semantics — files no longer in staging are removed from the
    marketplace plugin dir.
    """
    rsync = shutil.which("rsync")
    if not rsync:
        raise PublishFailed("rsync not found in PATH")
    marketplace_plugin_dir.mkdir(parents=True, exist_ok=True)
    src = str(staging).rstrip("/") + "/"
    dst = str(marketplace_plugin_dir).rstrip("/") + "/"
    proc = _run([rsync, *DEFAULT_RSYNC_FLAGS, src, dst])
    if proc.returncode != 0:
        raise PublishFailed(
            f"rsync failed: {proc.stderr.strip() or proc.stdout.strip()}"
        )


def _build_commit_message(
    manifest: Manifest,
    clones: dict[str, ClonedSource],
    builder_version: str,
) -> str:
    """AC-6 — commit message includes builder_version and at least one source SHA."""
    source_parts = [
        f"{sid}@{clone.resolved_sha}" for sid, clone in clones.items()
    ]
    sources_str = "sources: " + " ".join(source_parts)
    return (
        f"{manifest.plugin.name}: built from {builder_version} | {sources_str}"
    )


def _commit_and_push(
    marketplace_repo: Path, message: str, branch: str
) -> PublishResult:
    """git add -A → check porcelain (skip if empty) → commit → push (1 retry on non-fast-forward)."""
    add = _run(["git", "add", "-A"], cwd=marketplace_repo)
    if add.returncode != 0:
        raise PublishFailed(f"git add failed: {add.stderr.strip()}")

    status = _run(["git", "status", "--porcelain"], cwd=marketplace_repo)
    if status.returncode != 0:
        raise PublishFailed(f"git status failed: {status.stderr.strip()}")
    if not status.stdout.strip():
        # No changes — skip commit + push (B.8 step 2)
        return PublishResult(pushed=False, commit_sha=None, commit_message=message)

    commit = _run(["git", "commit", "-m", message], cwd=marketplace_repo)
    if commit.returncode != 0:
        raise PublishFailed(f"git commit failed: {commit.stderr.strip()}")

    head = _run(["git", "rev-parse", "HEAD"], cwd=marketplace_repo)
    if head.returncode != 0:
        raise PublishFailed(f"git rev-parse HEAD failed: {head.stderr.strip()}")
    commit_sha = head.stdout.strip()

    push = _run(["git", "push", "origin", branch], cwd=marketplace_repo)
    if push.returncode != 0:
        # One-shot retry via fetch + rebase + push
        fetch = _run(["git", "fetch", "origin", branch], cwd=marketplace_repo)
        if fetch.returncode != 0:
            raise PublishFailed(
                f"git push failed and fetch retry failed: {push.stderr.strip()} / {fetch.stderr.strip()}"
            )
        rebase = _run(
            ["git", "rebase", f"origin/{branch}"], cwd=marketplace_repo
        )
        if rebase.returncode != 0:
            raise PublishFailed(
                f"git push failed and rebase retry failed: {rebase.stderr.strip()}"
            )
        push2 = _run(["git", "push", "origin", branch], cwd=marketplace_repo)
        if push2.returncode != 0:
            raise PublishFailed(
                f"git push failed after rebase retry: {push2.stderr.strip()}"
            )

    return PublishResult(pushed=True, commit_sha=commit_sha, commit_message=message)


def verify_marketplace_unchanged_on_failure(
    marketplace_repo: Path, pre_build_head: str
) -> None:
    """FR-9 invariant — HEAD must equal pre-build SHA when publish failed."""
    proc = _run(["git", "rev-parse", "HEAD"], cwd=marketplace_repo)
    if proc.returncode != 0:
        raise PublishFailed(
            f"could not verify marketplace HEAD: {proc.stderr.strip()}"
        )
    current = proc.stdout.strip()
    if current != pre_build_head:
        raise PublishFailed(
            f"FR-9 invariant violated: marketplace HEAD changed from "
            f"{pre_build_head} to {current} despite publish failure"
        )


def publish_to_marketplace(
    staging_dir: Path,
    marketplace_repo: Path,
    manifest: Manifest,
    clones: dict[str, ClonedSource],
    builder_version: str,
) -> PublishResult:
    """End-to-end atomic publish: rsync → commit → push.

    On any failure, raises PublishFailed and verifies the marketplace
    HEAD is unchanged (FR-9-A2).
    """
    marketplace_repo = Path(marketplace_repo)
    pre_head_proc = _run(["git", "rev-parse", "HEAD"], cwd=marketplace_repo)
    if pre_head_proc.returncode != 0:
        raise PublishFailed(
            f"could not capture pre-build HEAD: {pre_head_proc.stderr.strip()}"
        )
    pre_head = pre_head_proc.stdout.strip()
    branch = _get_default_branch(marketplace_repo)
    message = _build_commit_message(manifest, clones, builder_version)

    plugin_dir = marketplace_repo / MARKETPLACE_PLUGIN_SUBDIR
    try:
        _rsync_staging(staging_dir, plugin_dir)
        result = _commit_and_push(marketplace_repo, message, branch)
    except PublishFailed:
        # Best-effort invariant check; if HEAD changed we re-raise with note
        try:
            verify_marketplace_unchanged_on_failure(marketplace_repo, pre_head)
        except PublishFailed as inv:
            raise inv  # invariant violation supersedes original
        raise

    return result
