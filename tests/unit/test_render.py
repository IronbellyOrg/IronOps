"""Unit tests for ironops.render — FR-1/FR-4/FR-7/FR-8/NFR-1 coverage."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from ironops.errors import CoImportMissing, PathEscape, UnresolvedImport
from ironops.manifest import (
    ImportSpec,
    Manifest,
    MarketplaceSpec,
    PluginSpec,
    SourceSpec,
)
from ironops.render import (
    enforce_co_imports,
    enforce_path_safety,
    render_to_staging,
)
from ironops.sources import ClonedSource


def _make_clone(tmp_path: Path) -> tuple[Path, dict[str, ClonedSource]]:
    """Build a small fake upstream tree under tmp_path."""
    root = tmp_path / "upstream"
    agents = root / "src" / "superclaude" / "agents"
    skills = root / "src" / "superclaude" / "skills" / "sc-foo-protocol"
    commands = root / "src" / "superclaude" / "commands"
    for d in (agents, skills, commands):
        d.mkdir(parents=True)
    (agents / "a1.md").write_text("# agent 1\n")
    (skills / "SKILL.md").write_text("# foo skill\n")
    (skills / "refs.md").write_text("# refs\n")
    (commands / "cmd1.md").write_text("# cmd1\nSkill sc:foo-protocol\n")
    return root, {
        "src": ClonedSource(
            id="src", path=root, resolved_ref="main", resolved_sha="a" * 40
        )
    }


def _make_manifest(imports):
    return Manifest(
        schema_version="1",
        sources={"src": SourceSpec(id="src", url="file:///x")},
        imports=imports,
        plugin=PluginSpec(name="p", description="d"),
        marketplace=MarketplaceSpec(name="m"),
        raw_sha256="0" * 64,
    )


def test_single_file_emits_one_rendered_file(tmp_path):
    root, clones = _make_clone(tmp_path)
    staging = tmp_path / "staging"
    m = _make_manifest(
        [
            ImportSpec(
                source="src",
                from_path="src/superclaude/agents/a1.md",
                to="agents/a1.md",
                kind="agent",
            )
        ]
    )
    out = render_to_staging(m, clones, staging)
    assert len(out) == 1
    assert (staging / "agents" / "a1.md").exists()


def test_directory_import_expands_fanout(tmp_path):
    root, clones = _make_clone(tmp_path)
    staging = tmp_path / "staging"
    m = _make_manifest(
        [
            ImportSpec(
                source="src",
                from_path="src/superclaude/skills/sc-foo-protocol/",
                to="skills/sc-foo-protocol/",
                kind="skill",
            )
        ]
    )
    out = render_to_staging(m, clones, staging)
    assert len(out) == 2  # SKILL.md + refs.md
    assert (staging / "skills" / "sc-foo-protocol" / "SKILL.md").exists()
    assert (staging / "skills" / "sc-foo-protocol" / "refs.md").exists()


def test_byte_identical_copy(tmp_path):
    """FR-7 — file bytes must be identical after copy."""
    root, clones = _make_clone(tmp_path)
    staging = tmp_path / "staging"
    m = _make_manifest(
        [
            ImportSpec(
                source="src",
                from_path="src/superclaude/agents/a1.md",
                to="agents/a1.md",
                kind="agent",
            )
        ]
    )
    render_to_staging(m, clones, staging)
    src_bytes = (root / "src" / "superclaude" / "agents" / "a1.md").read_bytes()
    dst_bytes = (staging / "agents" / "a1.md").read_bytes()
    assert (
        hashlib.sha256(src_bytes).hexdigest() == hashlib.sha256(dst_bytes).hexdigest()
    )


def test_co_import_command_with_skill_passes(tmp_path):
    """FR-4 — command + companion skill = no error."""
    root, clones = _make_clone(tmp_path)
    staging = tmp_path / "staging"
    m = _make_manifest(
        [
            ImportSpec(
                source="src",
                from_path="src/superclaude/skills/sc-foo-protocol/",
                to="skills/sc-foo-protocol/",
                kind="skill",
            ),
            ImportSpec(
                source="src",
                from_path="src/superclaude/commands/cmd1.md",
                to="commands/cmd1.md",
                kind="command",
            ),
        ]
    )
    out = render_to_staging(m, clones, staging)
    enforce_co_imports(out)  # no raise


def test_co_import_command_without_skill_fails(tmp_path):
    """FR-4-A1 — command without companion skill = CoImportMissing."""
    root, clones = _make_clone(tmp_path)
    staging = tmp_path / "staging"
    m = _make_manifest(
        [
            ImportSpec(
                source="src",
                from_path="src/superclaude/commands/cmd1.md",
                to="commands/cmd1.md",
                kind="command",
            ),
        ]
    )
    out = render_to_staging(m, clones, staging)
    with pytest.raises(CoImportMissing) as exc:
        enforce_co_imports(out)
    msg = str(exc.value)
    # FR-4-A1 — error message names both skill and citing command
    assert "sc-foo-protocol" in msg
    assert "cmd1.md" in msg


def test_co_import_skill_without_command_warns(tmp_path):
    """FR-4-A2 — skill imported without citing command is a warning, not failure."""
    root, clones = _make_clone(tmp_path)
    staging = tmp_path / "staging"
    m = _make_manifest(
        [
            ImportSpec(
                source="src",
                from_path="src/superclaude/skills/sc-foo-protocol/",
                to="skills/sc-foo-protocol/",
                kind="skill",
            ),
        ]
    )
    out = render_to_staging(m, clones, staging)
    with pytest.warns(UserWarning):
        enforce_co_imports(out)


@pytest.mark.parametrize(
    "escape_to",
    ["../../etc/passwd", "/etc/passwd"],
    ids=["dotdot", "absolute-unix"],
)
def test_path_escape_in_to_field_rejected(tmp_path, escape_to):
    """FR-8 — import.to with absolute path or .. segment is rejected."""
    root, clones = _make_clone(tmp_path)
    staging = tmp_path / "staging"
    m = _make_manifest(
        [
            ImportSpec(
                source="src",
                from_path="src/superclaude/agents/a1.md",
                to=escape_to,
                kind="agent",
            )
        ]
    )
    with pytest.raises(PathEscape):
        render_to_staging(m, clones, staging)


def test_unresolved_import_raises(tmp_path):
    root, clones = _make_clone(tmp_path)
    staging = tmp_path / "staging"
    m = _make_manifest(
        [
            ImportSpec(
                source="src",
                from_path="src/superclaude/agents/missing.md",
                to="agents/missing.md",
                kind="agent",
            )
        ]
    )
    with pytest.raises(UnresolvedImport):
        render_to_staging(m, clones, staging)


def test_path_safety_allows_claude_plugin_root(tmp_path):
    """FR-8 — ${CLAUDE_PLUGIN_ROOT}/... is allowed."""
    f = tmp_path / "x.md"
    f.write_text("see ${CLAUDE_PLUGIN_ROOT}/agents/foo.md")
    enforce_path_safety(f, tmp_path)  # no raise


def test_deterministic_ordering(tmp_path):
    """NFR-1 — two runs with identical inputs produce identical RenderedFile ordering."""
    root, clones = _make_clone(tmp_path)
    staging1 = tmp_path / "staging1"
    staging2 = tmp_path / "staging2"
    imports = [
        ImportSpec(
            source="src",
            from_path="src/superclaude/skills/sc-foo-protocol/",
            to="skills/sc-foo-protocol/",
            kind="skill",
        ),
        ImportSpec(
            source="src",
            from_path="src/superclaude/agents/a1.md",
            to="agents/a1.md",
            kind="agent",
        ),
    ]
    m = _make_manifest(imports)
    out1 = render_to_staging(m, clones, staging1)
    out2 = render_to_staging(m, clones, staging2)
    rel1 = [str(rf.to_path.relative_to(staging1)) for rf in out1]
    rel2 = [str(rf.to_path.relative_to(staging2)) for rf in out2]
    assert rel1 == rel2
