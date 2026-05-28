"""Unit tests for ironops.manifest — FR-1/FR-14/FR-15/FR-16 guard coverage."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from ironops.errors import ManifestInvalid, SelfOverwrite
from ironops.manifest import RESERVED_GENERATED_PATHS, Manifest, load_manifest


def _write(path: Path, content: str) -> Path:
    path.write_text(textwrap.dedent(content))
    return path


def _valid_yaml(extra_imports: str = "") -> str:
    return (
        """
    schema_version: "1"
    sources:
      ironclaude:
        url: "file:///x"
    imports:
      - source: ironclaude
        from: "src/agents/devops-architect.md"
        to: "agents/devops-architect.md"
        kind: agent
    """
        + (extra_imports or "")
        + """
    plugin:
      name: "ironops-devops"
      description: "test"
    marketplace:
      name: "ironops"
      owner:
        name: "IronbellyOrg"
    """
    )


def test_good_manifest_loads(tmp_path):
    p = _write(tmp_path / "m.yaml", _valid_yaml())
    m = load_manifest(p)
    assert isinstance(m, Manifest)
    assert m.schema_version == "1"
    assert m.plugin.name == "ironops-devops"
    assert len(m.imports) == 1
    assert m.imports[0].kind == "agent"


@pytest.mark.parametrize(
    "raw,reason",
    [
        ('"999"', "999"),
        ('"1.0"', "1.0"),
        ('"1.x"', "1.x"),
        ("1", "int 1"),
    ],
    ids=["v999", "dotted-1.0", "dotted-1.x", "int-1"],
)
def test_schema_version_negative(tmp_path, raw, reason):
    yml = _valid_yaml().replace('schema_version: "1"', f"schema_version: {raw}")
    p = _write(tmp_path / "m.yaml", yml)
    with pytest.raises(ManifestInvalid) as exc:
        load_manifest(p)
    assert "schema_version" in str(exc.value).lower()


def test_schema_version_missing(tmp_path):
    yml = _valid_yaml().replace('schema_version: "1"', "")
    p = _write(tmp_path / "m.yaml", yml)
    with pytest.raises(ManifestInvalid):
        load_manifest(p)


def test_empty_imports_rejected(tmp_path):
    yml = _valid_yaml().replace(
        'imports:\n      - source: ironclaude\n        from: "src/agents/devops-architect.md"\n        to: "agents/devops-architect.md"\n        kind: agent\n    ',
        "imports: []\n    ",
    )
    p = _write(tmp_path / "m.yaml", yml)
    with pytest.raises(ManifestInvalid) as exc:
        load_manifest(p)
    assert "imports" in str(exc.value).lower()


def test_missing_imports_key_rejected(tmp_path):
    yml = """
    schema_version: "1"
    sources:
      ironclaude:
        url: "file:///x"
    plugin:
      name: "ironops-devops"
      description: "test"
    marketplace:
      name: "ironops"
      owner:
        name: "IronbellyOrg"
    """
    p = _write(tmp_path / "m.yaml", yml)
    with pytest.raises(ManifestInvalid):
        load_manifest(p)


@pytest.mark.parametrize("reserved", sorted(RESERVED_GENERATED_PATHS))
def test_self_overwrite_rejected(tmp_path, reserved):
    yml = _valid_yaml().replace(
        'to: "agents/devops-architect.md"',
        f'to: "{reserved}"',
    )
    p = _write(tmp_path / "m.yaml", yml)
    with pytest.raises(SelfOverwrite) as exc:
        load_manifest(p)
    assert reserved in str(exc.value)


def test_hook_kind_rejected(tmp_path):
    yml = _valid_yaml().replace("kind: agent", "kind: hook-config")
    p = _write(tmp_path / "m.yaml", yml)
    with pytest.raises(ManifestInvalid) as exc:
        load_manifest(p)
    assert (
        "hook-config" in str(exc.value).lower() or "reserved" in str(exc.value).lower()
    )


def test_unknown_source_id_rejected(tmp_path):
    yml = _valid_yaml().replace("source: ironclaude", "source: unknown-src")
    p = _write(tmp_path / "m.yaml", yml)
    with pytest.raises(ManifestInvalid) as exc:
        load_manifest(p)
    assert "unknown" in str(exc.value).lower() or "source" in str(exc.value).lower()


def test_non_kebab_plugin_name_rejected(tmp_path):
    yml = _valid_yaml().replace('name: "ironops-devops"', 'name: "IronOps_DevOps"')
    p = _write(tmp_path / "m.yaml", yml)
    with pytest.raises(ManifestInvalid) as exc:
        load_manifest(p)
    assert "kebab" in str(exc.value).lower() or "name" in str(exc.value).lower()


def test_raw_sha256_recorded(tmp_path):
    p = _write(tmp_path / "m.yaml", _valid_yaml())
    m = load_manifest(p)
    assert m.raw_sha256
    assert len(m.raw_sha256) == 64
    # deterministic — same content yields same sha
    p2 = _write(tmp_path / "m2.yaml", _valid_yaml())
    assert m.raw_sha256 == load_manifest(p2).raw_sha256


def test_missing_file_rejected(tmp_path):
    with pytest.raises(ManifestInvalid):
        load_manifest(tmp_path / "nope.yaml")
