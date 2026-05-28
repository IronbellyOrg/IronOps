"""Unit tests for ironops.metadata — FR-6/FR-10/FR-11/FR-12/FR-13 + AC-4/AC-5/AC-6."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from ironops import metadata
from ironops.errors import BuilderDirtyTree
from ironops.manifest import (
    ImportSpec,
    Manifest,
    MarketplaceSpec,
    PluginSpec,
    SourceSpec,
)
from ironops.render import RenderedFile
from ironops.sources import ClonedSource


@pytest.fixture
def synth_inputs(tmp_path):
    m = Manifest(
        schema_version="1",
        sources={"src": SourceSpec(id="src", url="file:///x")},
        imports=[
            ImportSpec(source="src", from_path="a.md", to="agents/a.md", kind="agent"),
        ],
        plugin=PluginSpec(name="ironops-devops", description="DevOps plugin"),
        marketplace=MarketplaceSpec(name="ironops", owner={"name": "IronbellyOrg"}),
        raw_sha256="d" * 64,
    )
    clones = {"src": ClonedSource(id="src", path=tmp_path / "src-clone", resolved_ref="main", resolved_sha="e" * 40)}
    (tmp_path / "src-clone").mkdir(exist_ok=True)
    rendered = [RenderedFile(
        from_path=tmp_path / "src-clone" / "a.md",
        to_path=tmp_path / "staging" / "agents" / "a.md",
        kind="agent",
        source_id="src",
    )]
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "agents").mkdir()
    (staging / "agents" / "a.md").write_text("# a\n")
    return m, clones, rendered, staging


def test_plugin_json_omits_version(synth_inputs):
    m, clones, rendered, staging = synth_inputs
    out = metadata.write_plugin_json(m, staging)
    data = json.loads(out.read_text())
    assert "version" not in data, "FR-13-A1 — plugin.json MUST NOT contain a version key"
    assert data["name"] == "ironops-devops"
    assert data["description"] == "DevOps plugin"


def test_plugin_json_required_keys(synth_inputs):
    m, clones, rendered, staging = synth_inputs
    out = metadata.write_plugin_json(m, staging)
    data = json.loads(out.read_text())
    assert set(data.keys()) == {"name", "description"}


def test_meta_json_schema_version_string_1(synth_inputs):
    m, clones, rendered, staging = synth_inputs
    metadata.write_meta_json(m, clones, rendered, staging, "f" * 40)
    data = json.loads((staging / "META.json").read_text())
    assert data["schema_version"] == "1"


def test_meta_json_built_at_iso8601_utc(synth_inputs):
    m, clones, rendered, staging = synth_inputs
    metadata.write_meta_json(m, clones, rendered, staging, "f" * 40)
    data = json.loads((staging / "META.json").read_text())
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", data["built_at"])


def test_meta_json_builder_version_is_40_hex(synth_inputs):
    m, clones, rendered, staging = synth_inputs
    metadata.write_meta_json(m, clones, rendered, staging, "f" * 40)
    data = json.loads((staging / "META.json").read_text())
    assert re.match(r"^[0-9a-f]{40}$", data["builder_version"])


def test_meta_json_manifest_sha256_matches(synth_inputs):
    m, clones, rendered, staging = synth_inputs
    metadata.write_meta_json(m, clones, rendered, staging, "f" * 40)
    data = json.loads((staging / "META.json").read_text())
    assert data["manifest_sha256"] == m.raw_sha256


def test_meta_json_sources_imports_fanout(synth_inputs):
    m, clones, rendered, staging = synth_inputs
    metadata.write_meta_json(m, clones, rendered, staging, "f" * 40)
    data = json.loads((staging / "META.json").read_text())
    assert len(data["sources"]) == 1
    assert data["sources"][0]["id"] == "src"
    assert len(data["sources"][0]["imports"]) == 1
    assert data["sources"][0]["imports"][0]["kind"] == "agent"


def test_meta_json_summary_counts(synth_inputs):
    m, clones, rendered, staging = synth_inputs
    metadata.write_meta_json(m, clones, rendered, staging, "f" * 40)
    data = json.loads((staging / "META.json").read_text())
    assert data["summary"]["total_files"] == 1
    assert data["summary"]["by_kind"] == {"agent": 1}


def test_third_party_licenses_references_upstream(synth_inputs):
    m, clones, rendered, staging = synth_inputs
    out = metadata.write_third_party_licenses(m, clones, rendered, staging)
    text = out.read_text()
    assert "Third-Party Licenses" in text
    assert "src" in text  # source id appears
    assert "agents/a.md" in text  # imported file listed


def test_third_party_licenses_per_file_mapping(synth_inputs):
    m, clones, rendered, staging = synth_inputs
    out = metadata.write_third_party_licenses(m, clones, rendered, staging)
    text = out.read_text()
    assert "agents/a.md" in text
    assert "kind:" in text


def test_marketplace_json_single_plugin(synth_inputs):
    m, clones, rendered, staging = synth_inputs
    out = metadata.write_marketplace_json(m, staging)
    data = json.loads(out.read_text())
    assert len(data["plugins"]) == 1


def test_marketplace_json_source_path(synth_inputs):
    """FR-10-A1 — marketplace.json source must be ./plugins/ironops-devops."""
    m, clones, rendered, staging = synth_inputs
    metadata.write_marketplace_json(m, staging)
    data = json.loads((staging / ".claude-plugin" / "marketplace.json").read_text())
    assert data["plugins"][0]["source"] == "./plugins/ironops-devops"


def test_resolve_builder_version_fails_on_dirty_tree(monkeypatch, tmp_path):
    """FR-12 — _resolve_builder_version must raise BuilderDirtyTree on non-empty porcelain."""
    real_run = subprocess.run

    def fake(cmd, *a, **kw):
        if "rev-parse" in cmd:
            return subprocess.CompletedProcess(cmd, 0, "a" * 40 + "\n", "")
        if "status" in cmd and "--porcelain" in cmd:
            return subprocess.CompletedProcess(cmd, 0, " M src/foo.py\n", "")
        return real_run(cmd, *a, **kw)
    monkeypatch.setattr(subprocess, "run", fake)
    with pytest.raises(BuilderDirtyTree):
        metadata._resolve_builder_version(tmp_path)
