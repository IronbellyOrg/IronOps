"""Copy upstream files into staging, enforce co-imports and path safety.

Implements FR-1 (copy per manifest entry), FR-3 (read-only upstream),
FR-4 (co-import enforcement: command-referencing-skill must have the
skill imported), FR-7 (byte-identical copy via ``shutil.copy2``),
FR-8 (path safety — reject absolute paths and ``..`` segments, allow
``${CLAUDE_PLUGIN_ROOT}/...``), and NFR-1 (deterministic ordering).
"""

from __future__ import annotations

import re
import shutil
import warnings
from dataclasses import dataclass
from pathlib import Path

from ironops.errors import CoImportMissing, PathEscape, UnresolvedImport
from ironops.manifest import ImportSpec, Manifest
from ironops.sources import ClonedSource

CLAUDE_PLUGIN_ROOT_VAR: str = "${CLAUDE_PLUGIN_ROOT}"

# FR-4 — find references to companion skill protocols inside command bodies
_SKILL_REF_RE = re.compile(r"Skill\s+(sc[:-][a-z0-9-]+(?:-protocol)?)")

# FR-8 — absolute path and dot-dot segment detection
_ABS_PATH_RES = [
    re.compile(r"(?<![A-Za-z0-9_])/(?:etc|root|home|var|usr|tmp|opt)/"),
    re.compile(r"(?<![A-Za-z0-9_/])(?:[A-Z]:[\\/])"),  # Windows drive
]
_DOTDOT_RE = re.compile(r"(?:^|[\\/])\.\.(?:[\\/]|$)")
_PLUGIN_ROOT_RE = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}")


@dataclass(frozen=True)
class RenderedFile:
    from_path: Path
    to_path: Path
    kind: str
    source_id: str


def _expand_one_import(
    imp: ImportSpec, source_root: Path, staging_dir: Path
) -> list[RenderedFile]:
    """Expand a single ImportSpec into one or more RenderedFile entries."""
    src = source_root / imp.from_path
    if not src.exists():
        raise UnresolvedImport(
            f"import {imp.source}:{imp.from_path!r} does not exist in upstream"
        )
    dst = staging_dir / imp.to
    out: list[RenderedFile] = []
    if src.is_file():
        out.append(
            RenderedFile(
                from_path=src,
                to_path=dst,
                kind=imp.kind,
                source_id=imp.source,
            )
        )
    else:
        # directory — expand to every file beneath (deterministic ordering)
        for child in sorted(src.rglob("*")):
            if child.is_file():
                rel = child.relative_to(src)
                out.append(
                    RenderedFile(
                        from_path=child,
                        to_path=dst / rel,
                        kind=imp.kind,
                        source_id=imp.source,
                    )
                )
    return out


def _copy_one_import(rf: RenderedFile) -> None:
    """FR-7 byte-identical copy via ``shutil.copy2``.

    Single-file ImportSpecs and per-file expansion of directory ImportSpecs
    both end here. ``shutil.copytree`` is not used because we pre-expand
    the directory into a list of RenderedFiles (deterministic ordering).
    """
    rf.to_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(rf.from_path, rf.to_path)


def _scan_command_for_skill_refs(path: Path) -> list[str]:
    """Return the skill protocol names referenced in a command file body."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    refs: list[str] = []
    for match in _SKILL_REF_RE.finditer(text):
        # normalize 'sc:foo-protocol' / 'sc-foo-protocol' → 'sc-foo-protocol'
        ref = match.group(1).replace(":", "-")
        refs.append(ref)
    return refs


def enforce_co_imports(rendered: list[RenderedFile]) -> None:
    """FR-4 — for every command import that references a Skill sc:<x>-protocol,
    the matching skill directory must also be imported. Reverse direction
    (skill present without citing command) is a warning, not a failure.
    """
    # Collect the set of imported skill protocol names from rendered staging paths
    imported_skills: set[str] = set()
    commands: list[RenderedFile] = []
    for rf in rendered:
        if rf.kind == "skill":
            # to_path is like '<staging>/skills/sc-foo-protocol/SKILL.md'
            parts = rf.to_path.parts
            if "skills" in parts:
                idx = parts.index("skills")
                if idx + 1 < len(parts):
                    imported_skills.add(parts[idx + 1])
        elif rf.kind == "command":
            commands.append(rf)

    cited_skills: set[str] = set()
    for cmd in commands:
        refs = _scan_command_for_skill_refs(cmd.from_path)
        for ref in refs:
            cited_skills.add(ref)
            if ref not in imported_skills:
                raise CoImportMissing(
                    f"command {cmd.to_path} references Skill sc:{ref[3:] if ref.startswith('sc-') else ref}-protocol "
                    f"but skill {ref!r} is not imported; add an import targeting "
                    f"'skills/{ref}/' to the manifest"
                )

    # FR-4-A2 — skill imported without citing command is a warning
    orphan_skills = imported_skills - cited_skills
    for orphan in sorted(orphan_skills):
        warnings.warn(
            f"skill {orphan!r} imported but no command references it (FR-4-A2)",
            stacklevel=2,
        )


def enforce_path_safety(file_path: Path, plugin_root: Path) -> None:
    """FR-8 — verify the emitted file resolves inside the plugin root.

    The primary FR-8 enforcement runs in ``render_to_staging`` against each
    import's ``to:`` field (rejecting absolute paths and ``..`` segments
    before any copy). This function provides a defensive post-copy check:
    every rendered file's resolved path must be a descendant of the staging
    directory. File contents are NOT scanned — documentation files
    legitimately reference real filesystem paths.
    """
    try:
        resolved = file_path.resolve()
        root = plugin_root.resolve()
    except OSError as exc:
        raise PathEscape(f"could not resolve {file_path}: {exc}") from exc
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PathEscape(
            f"file {file_path} resolves outside plugin root {plugin_root} (FR-8 violation)"
        ) from exc


def render_to_staging(
    manifest: Manifest,
    clones: dict[str, ClonedSource],
    staging_dir: Path,
) -> list[RenderedFile]:
    """Copy every import into the staging directory and return the fanout list.

    Imports are processed in sorted order by `to:` path (NFR-1 determinism).
    Returns the full list of RenderedFile entries, one per emitted file.
    """
    staging_dir = Path(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)

    # FR-8 path-safety pre-check on each import.to declaration
    for imp in manifest.imports:
        if Path(imp.to).is_absolute() or ".." in Path(imp.to).parts:
            raise PathEscape(f"import.to {imp.to!r} contains escape (absolute or '..')")

    # NFR-1 — deterministic ordering by `to:`
    sorted_imports = sorted(manifest.imports, key=lambda i: i.to)

    rendered: list[RenderedFile] = []
    for imp in sorted_imports:
        if imp.source not in clones:
            raise UnresolvedImport(
                f"import {imp.source}:{imp.from_path!r} — source not cloned"
            )
        clone = clones[imp.source]
        expanded = _expand_one_import(imp, clone.path, staging_dir)
        for rf in expanded:
            _copy_one_import(rf)
            rendered.append(rf)

    return rendered
