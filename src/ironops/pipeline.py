"""8-stage build orchestrator (spec §7 PREFLIGHT..REPORT).

Stages 0..7: PREFLIGHT → CLONE → READ MANIFEST → RENDER → WRITE METADATA →
VALIDATE → PUBLISH → REPORT.

Stage 1 CLONE necessarily depends on the parsed manifest (since the clone
loop iterates ``sources[*]``); the manifest is therefore parsed at the
start of Stage 1 and Stage 2 acts as a re-validation pass for spec
traceability. This is documented in the task checklist (Step 3.9).

All BuilderError subclasses raised by stage functions are caught at the
top level and translated into a structured ``BuildResult`` so the public
``run_build`` never raises (NFR-7 part a/b).
"""

from __future__ import annotations

import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ironops import errors as _errors_mod
from ironops import metadata, publish, render, sources, validate
from ironops.errors import BuilderError, ExitCode, format_failure
from ironops.manifest import Manifest, load_manifest
from ironops.sources import ClonedSource

SOFT_WARN_SECONDS: int = 60
HARD_FAIL_SECONDS: int = 300


@dataclass
class BuildContext:
    manifest_path: Path
    staging_dir: Path
    scratch_dir: Path
    marketplace_repo: Optional[Path] = None
    builder_version: Optional[str] = None
    dry_run: bool = False
    verbose: bool = False
    start_time: float = field(default_factory=time.monotonic)


@dataclass
class BuildResult:
    success: bool
    exit_code: ExitCode
    summary: str
    failure: Optional[BuilderError] = None
    manifest: Optional[Manifest] = None
    clones: dict[str, ClonedSource] = field(default_factory=dict)
    rendered: list = field(default_factory=list)
    publish_result: Optional[publish.PublishResult] = None
    duration_s: float = 0.0


def _log(ctx: BuildContext, message: str) -> None:
    if ctx.verbose:
        print(f"[ironops] {message}", file=sys.stderr)


def _check_timing(ctx: BuildContext) -> None:
    elapsed = time.monotonic() - ctx.start_time
    if elapsed > HARD_FAIL_SECONDS:
        raise RuntimeError(
            f"build exceeded {HARD_FAIL_SECONDS}s hard ceiling (NFR-2)"
        )
    if elapsed > SOFT_WARN_SECONDS and ctx.verbose:
        print(
            f"[ironops] warning: build elapsed {elapsed:.1f}s > {SOFT_WARN_SECONDS}s soft (NFR-2)",
            file=sys.stderr,
        )


def _stage_0_preflight(ctx: BuildContext) -> str:
    """Verify python/git/rsync, resolve builder version (also enforces FR-12)."""
    _log(ctx, "stage 0: preflight")
    for tool in ("git", "rsync"):
        if not shutil.which(tool):
            raise RuntimeError(f"required tool {tool!r} not found in PATH")
    # FR-12 dirty-tree enforcement runs here via _resolve_builder_version
    builder_version = metadata._resolve_builder_version()
    ctx.builder_version = builder_version
    return builder_version


def _stage_1_clone(
    ctx: BuildContext, manifest: Manifest
) -> dict[str, ClonedSource]:
    """Shallow-clone every upstream source declared in the manifest."""
    _log(ctx, "stage 1: clone")
    return sources.clone_sources(manifest, ctx.scratch_dir)


def _stage_2_read_manifest(ctx: BuildContext) -> Manifest:
    """Parse + validate the manifest (FR-1/14/15/16)."""
    _log(ctx, "stage 2: read manifest")
    return load_manifest(ctx.manifest_path)


def _stage_3_render(
    ctx: BuildContext, manifest: Manifest, clones: dict[str, ClonedSource]
) -> list[render.RenderedFile]:
    """Copy imports into staging, enforce co-imports, enforce path safety."""
    _log(ctx, "stage 3: render")
    rendered = render.render_to_staging(manifest, clones, ctx.staging_dir)
    render.enforce_co_imports(rendered)
    for rf in rendered:
        render.enforce_path_safety(rf.to_path, ctx.staging_dir)
    return rendered


def _stage_4_write_metadata(
    ctx: BuildContext,
    manifest: Manifest,
    clones: dict[str, ClonedSource],
    rendered: list[render.RenderedFile],
    builder_version: str,
) -> None:
    """Emit plugin.json, META.json, THIRD_PARTY_LICENSES.md, marketplace.json."""
    _log(ctx, "stage 4: write metadata")
    metadata.write_plugin_json(manifest, ctx.staging_dir)
    metadata.write_meta_json(
        manifest, clones, rendered, ctx.staging_dir, builder_version
    )
    metadata.write_third_party_licenses(
        manifest, clones, rendered, ctx.staging_dir
    )
    metadata.write_marketplace_json(manifest, ctx.staging_dir)


def _stage_5_validate(ctx: BuildContext) -> Optional[validate.ValidatorResult]:
    """Run ``claude plugin validate``. Skipped only when claude binary is unavailable."""
    _log(ctx, "stage 5: validate")
    try:
        return validate.run_validator(ctx.staging_dir, log_dir=ctx.staging_dir)
    except RuntimeError as exc:
        # claude binary not installed — log and continue (Phase 7.9 guard)
        _log(ctx, f"stage 5: validator skipped ({exc})")
        return None


def _stage_6_publish(
    ctx: BuildContext,
    manifest: Manifest,
    clones: dict[str, ClonedSource],
    builder_version: str,
) -> Optional[publish.PublishResult]:
    """Atomic publish to marketplace repo. Skipped when dry_run=True or no marketplace_repo."""
    _log(ctx, "stage 6: publish")
    if ctx.dry_run:
        _log(ctx, "stage 6: skipped (dry_run)")
        return None
    if ctx.marketplace_repo is None:
        _log(ctx, "stage 6: skipped (no marketplace_repo)")
        return None
    return publish.publish_to_marketplace(
        ctx.staging_dir,
        ctx.marketplace_repo,
        manifest,
        clones,
        builder_version,
    )


def _stage_7_report(
    ctx: BuildContext,
    manifest: Manifest,
    clones: dict[str, ClonedSource],
    rendered: list[render.RenderedFile],
    publish_result: Optional[publish.PublishResult],
) -> str:
    """Stdout summary with counts + SHAs + push status."""
    _log(ctx, "stage 7: report")
    parts = [
        f"plugin={manifest.plugin.name}",
        f"files={len(rendered)}",
        f"sources={','.join(f'{sid}@{c.resolved_sha[:8]}' for sid, c in clones.items())}",
    ]
    if publish_result is not None:
        parts.append(f"pushed={publish_result.pushed}")
        if publish_result.commit_sha:
            parts.append(f"commit={publish_result.commit_sha[:8]}")
    elif ctx.dry_run:
        parts.append("publish=skipped(dry_run)")
    return " ".join(parts)


def run_build(ctx: BuildContext) -> BuildResult:
    """Run the full 8-stage pipeline. Never raises BuilderError out of this method."""
    ctx.start_time = time.monotonic()
    try:
        builder_version = _stage_0_preflight(ctx)
        _check_timing(ctx)
        # Stage 1 needs the manifest to know what to clone — parse first
        manifest = _stage_2_read_manifest(ctx)
        clones = _stage_1_clone(ctx, manifest)
        _check_timing(ctx)
        # Stage 2 re-validation pass for spec traceability
        # (already done by load_manifest; this is a no-op re-assertion)
        rendered = _stage_3_render(ctx, manifest, clones)
        _check_timing(ctx)
        _stage_4_write_metadata(ctx, manifest, clones, rendered, builder_version)
        _check_timing(ctx)
        _stage_5_validate(ctx)
        _check_timing(ctx)
        publish_result = _stage_6_publish(ctx, manifest, clones, builder_version)
        _check_timing(ctx)
        summary = _stage_7_report(ctx, manifest, clones, rendered, publish_result)
        duration_s = time.monotonic() - ctx.start_time
        return BuildResult(
            success=True,
            exit_code=ExitCode.SUCCESS,
            summary=summary,
            manifest=manifest,
            clones=clones,
            rendered=rendered,
            publish_result=publish_result,
            duration_s=duration_s,
        )
    except BuilderError as err:
        duration_s = time.monotonic() - ctx.start_time
        return BuildResult(
            success=False,
            exit_code=err.code,
            summary=format_failure(err),
            failure=err,
            duration_s=duration_s,
        )
    except Exception as exc:  # pragma: no cover — unexpected
        duration_s = time.monotonic() - ctx.start_time
        internal = _errors_mod.BuilderError(f"internal error: {exc}")
        internal.code = ExitCode.INTERNAL_ERROR
        return BuildResult(
            success=False,
            exit_code=ExitCode.INTERNAL_ERROR,
            summary=format_failure(internal),
            failure=internal,
            duration_s=duration_s,
        )
