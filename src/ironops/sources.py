"""Upstream repository cloning, default-branch resolution, SHA recording.

Implements FR-2 (always-latest mainline; default branch programmatically
resolved — no hardcoded ``main``/``master``), FR-3 (read-only upstream),
and NFR-9 (post-build clean working tree).
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ironops.errors import UpstreamCloneFailed
from ironops.manifest import Manifest, SourceSpec

CLONE_DEPTH: int = 1
GIT_TIMEOUT_SECONDS: int = 60

_SYMREF_RE = re.compile(r"^ref:\s+refs/heads/(\S+)\s+HEAD", re.MULTILINE)
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class ClonedSource:
    id: str
    path: Path
    resolved_ref: str
    resolved_sha: str


def _resolve_default_branch(url: str) -> str:
    """Resolve a remote's default branch via ``git ls-remote --symref``.

    Runs against the URL alone so it can execute BEFORE the shallow clone.
    Returns the branch name (e.g. ``main``, ``master``, ``develop``).
    Raises UpstreamCloneFailed if the symref line cannot be parsed (no
    fallback to ``main``/``master`` per FR-2-A3).
    """
    proc = subprocess.run(
        ["git", "ls-remote", "--symref", url, "HEAD"],
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_SECONDS,
        check=False,
    )
    if proc.returncode != 0:
        raise UpstreamCloneFailed(
            f"git ls-remote failed for {url!r}: {proc.stderr.strip()}"
        )
    m = _SYMREF_RE.search(proc.stdout)
    if not m:
        raise UpstreamCloneFailed(
            f"could not parse symref from ls-remote output for {url!r}"
        )
    return m.group(1)


def _shallow_clone(url: str, ref: str, dest: Path) -> None:
    """Invoke ``git clone --depth=1 --branch <ref> <url> <dest>``."""
    proc = subprocess.run(
        [
            "git",
            "clone",
            f"--depth={CLONE_DEPTH}",
            "--branch",
            ref,
            url,
            str(dest),
        ],
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_SECONDS,
        check=False,
    )
    if proc.returncode != 0:
        raise UpstreamCloneFailed(
            f"git clone failed for {url!r} @ {ref!r}: {proc.stderr.strip()}"
        )


def _resolve_sha(path: Path) -> str:
    """Read the resolved 40-hex SHA via ``git -C <path> rev-parse HEAD``."""
    proc = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_SECONDS,
        check=False,
    )
    if proc.returncode != 0:
        raise UpstreamCloneFailed(
            f"git rev-parse HEAD failed at {path}: {proc.stderr.strip()}"
        )
    sha = proc.stdout.strip()
    if not _SHA_RE.match(sha):
        raise UpstreamCloneFailed(
            f"git rev-parse returned invalid SHA at {path}: {sha!r}"
        )
    return sha


def _verify_clean_working_tree(path: Path) -> None:
    """NFR-9 invariant — ``git status --porcelain`` must be empty after build.

    Violation indicates a builder bug (we wrote into the upstream clone).
    Raises RuntimeError (not a categorical code) because this is an
    internal invariant violation, not a user-facing failure.
    """
    proc = subprocess.run(
        ["git", "-C", str(path), "status", "--porcelain"],
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_SECONDS,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git status failed in upstream clone at {path}: {proc.stderr.strip()}"
        )
    if proc.stdout.strip():
        raise RuntimeError(
            f"upstream clone at {path} is not clean after build (NFR-9 violation): {proc.stdout!r}"
        )


def _clone_one(spec: SourceSpec, dest: Path) -> ClonedSource:
    if spec.sha and spec.ref:
        raise UpstreamCloneFailed(
            f"source {spec.id!r}: ref and sha are mutually exclusive"
        )
    if spec.ref:
        ref = spec.ref
    else:
        ref = _resolve_default_branch(spec.url)
    _shallow_clone(spec.url, ref, dest)
    resolved_sha = _resolve_sha(dest)
    if spec.sha and spec.sha != resolved_sha:
        raise UpstreamCloneFailed(
            f"source {spec.id!r}: requested sha {spec.sha!r} != resolved {resolved_sha!r}"
        )
    return ClonedSource(
        id=spec.id, path=dest, resolved_ref=ref, resolved_sha=resolved_sha
    )


def clone_sources(
    manifest: Manifest, scratch_dir: Path
) -> dict[str, ClonedSource]:
    """Clone every source declared in the manifest into ``scratch_dir``."""
    scratch_dir = Path(scratch_dir)
    scratch_dir.mkdir(parents=True, exist_ok=True)
    out: dict[str, ClonedSource] = {}
    for source_id, spec in manifest.sources.items():
        dest = scratch_dir / source_id
        if dest.exists():
            raise UpstreamCloneFailed(
                f"scratch destination {dest} already exists"
            )
        out[source_id] = _clone_one(spec, dest)
    return out
