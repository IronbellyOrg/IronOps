"""Provenance metadata emitters.

Emits ``plugin.json`` (FR-13 — no version key), ``META.json`` (FR-6 —
provenance), ``THIRD_PARTY_LICENSES.md`` (FR-11), and
``marketplace.json`` (FR-10). Builder version is resolved by
``_resolve_builder_version`` which raises ``BuilderDirtyTree`` per
FR-12 + disposition D5 (no ``--allow-dirty`` override).
"""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from ironops.errors import BuilderDirtyTree
from ironops.manifest import Manifest
from ironops.render import RenderedFile
from ironops.sources import ClonedSource

META_JSON_SCHEMA_VERSION: str = "1"
PLUGIN_JSON_FILENAME: str = ".claude-plugin/plugin.json"
META_JSON_FILENAME: str = "META.json"
LICENSES_FILENAME: str = "THIRD_PARTY_LICENSES.md"
MARKETPLACE_JSON_PATH: str = ".claude-plugin/marketplace.json"

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _resolve_builder_version(ironops_repo_root: Path | None = None) -> str:
    """Resolve the builder's git SHA from the IronOps repo.

    Raises BuilderDirtyTree per FR-12 + D5 if ``git status --porcelain``
    reports any modifications (no ``--allow-dirty`` override).
    """
    if ironops_repo_root is None:
        ironops_repo_root = Path(__file__).resolve().parents[2]

    sha_proc = subprocess.run(
        ["git", "-C", str(ironops_repo_root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if sha_proc.returncode != 0:
        raise BuilderDirtyTree(
            f"could not resolve IronOps git SHA: {sha_proc.stderr.strip()}"
        )
    sha = sha_proc.stdout.strip()
    if not _SHA_RE.match(sha):
        raise BuilderDirtyTree(f"resolved SHA is not 40-char hex: {sha!r}")

    porc_proc = subprocess.run(
        ["git", "-C", str(ironops_repo_root), "status", "--porcelain"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if porc_proc.returncode != 0:
        raise BuilderDirtyTree(
            f"git status failed in IronOps repo: {porc_proc.stderr.strip()}"
        )
    if porc_proc.stdout.strip():
        raise BuilderDirtyTree(
            "IronOps working tree is dirty (FR-12) — commit or stash before building"
        )
    return sha


def write_plugin_json(manifest: Manifest, staging_dir: Path) -> Path:
    """FR-13 — emits ``name`` and ``description`` only (no ``version`` key)."""
    out = Path(staging_dir) / PLUGIN_JSON_FILENAME
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": manifest.plugin.name,
        "description": manifest.plugin.description,
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return out


def write_meta_json(
    manifest: Manifest,
    clones: dict[str, ClonedSource],
    rendered: list[RenderedFile],
    staging_dir: Path,
    builder_version: str,
) -> Path:
    """FR-6 + §6 — emit META.json with full provenance.

    Includes: schema_version, plugin_name, built_at (ISO-8601 UTC),
    builder_version (40-char git SHA), manifest_sha256, sources[]
    (id, url, ref, sha, imports[] file-level fanout), and summary counts.
    """
    out = Path(staging_dir) / META_JSON_FILENAME

    # Group rendered files by source id for the sources[].imports[] fanout
    by_source: dict[str, list[RenderedFile]] = {}
    for rf in rendered:
        by_source.setdefault(rf.source_id, []).append(rf)

    kind_counts = Counter(rf.kind for rf in rendered)

    sources_block = []
    for source_id, source_spec in manifest.sources.items():
        clone = clones.get(source_id)

        def _from_rel(rf: RenderedFile) -> str:
            """Render `from:` as a path relative to the clone root for determinism (NFR-1)."""
            if clone is not None:
                try:
                    return str(rf.from_path.relative_to(clone.path))
                except ValueError:
                    pass
            return str(rf.from_path)

        sources_block.append(
            {
                "id": source_id,
                "url": source_spec.url,
                "ref": clone.resolved_ref if clone else None,
                "sha": clone.resolved_sha if clone else None,
                "imports": [
                    {
                        "from": _from_rel(rf),
                        "to": str(rf.to_path.relative_to(staging_dir)),
                        "kind": rf.kind,
                    }
                    for rf in sorted(
                        by_source.get(source_id, []), key=lambda r: str(r.to_path)
                    )
                ],
            }
        )

    payload = {
        "schema_version": META_JSON_SCHEMA_VERSION,
        "plugin_name": manifest.plugin.name,
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "builder_version": builder_version,
        "manifest_sha256": manifest.raw_sha256,
        "sources": sources_block,
        "summary": {
            "total_files": len(rendered),
            "by_kind": dict(sorted(kind_counts.items())),
        },
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return out


def write_third_party_licenses(
    manifest: Manifest,
    clones: dict[str, ClonedSource],
    rendered: list[RenderedFile],
    staging_dir: Path,
) -> Path:
    """FR-11 — per-source per-file attribution, referencing upstream LICENSE."""
    out = Path(staging_dir) / LICENSES_FILENAME
    lines: list[str] = ["# Third-Party Licenses", ""]
    lines.append(
        "This plugin redistributes content from the following upstream sources. "
        "Each upstream's LICENSE governs its contributed files."
    )
    lines.append("")
    by_source: dict[str, list[RenderedFile]] = {}
    for rf in rendered:
        by_source.setdefault(rf.source_id, []).append(rf)
    for source_id, source_spec in manifest.sources.items():
        clone = clones.get(source_id)
        lines.append(f"## {source_id}")
        lines.append("")
        lines.append(f"- URL: `{source_spec.url}`")
        if clone:
            lines.append(f"- Resolved ref: `{clone.resolved_ref}`")
            lines.append(f"- Resolved SHA: `{clone.resolved_sha}`")
            license_path = clone.path / "LICENSE"
            if license_path.exists():
                lines.append(
                    f"- Upstream LICENSE: `{source_id}/LICENSE` (see source repo)"
                )
        lines.append("")
        lines.append("### Imported files")
        lines.append("")
        for rf in sorted(by_source.get(source_id, []), key=lambda r: str(r.to_path)):
            rel = rf.to_path.relative_to(staging_dir)
            lines.append(f"- `{rel}` ← `{rf.from_path.name}` (kind: `{rf.kind}`)")
        lines.append("")
    out.write_text("\n".join(lines))
    return out


def write_marketplace_json(manifest: Manifest, staging_dir: Path) -> Path:
    """FR-10 — emit ``.claude-plugin/marketplace.json`` listing the single plugin."""
    out = Path(staging_dir) / MARKETPLACE_JSON_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": manifest.marketplace.name,
        "owner": manifest.marketplace.owner,
        "description": f"Curated Claude Code plugins from {manifest.marketplace.name}.",
        "plugins": [
            {
                "name": manifest.plugin.name,
                "description": manifest.plugin.description,
                "source": "./plugins/ironops-devops",
            }
        ],
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return out
