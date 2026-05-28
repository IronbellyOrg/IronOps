"""Unit tests for ironops.sources — FR-2/FR-3/NFR-9 coverage.

Uses monkeypatch.setattr on subprocess.run to inject controlled responses
for git ls-remote/clone/rev-parse/status without touching the network.
"""

from __future__ import annotations

import inspect
import subprocess

import pytest

from ironops import sources
from ironops.errors import UpstreamCloneFailed
from ironops.manifest import Manifest, MarketplaceSpec, PluginSpec, SourceSpec


def _make_completed(stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_no_hardcoded_main_or_master_in_module_source():
    """FR-2-A3 — module source must not contain hardcoded 'main' or 'master' branch names."""
    src = inspect.getsource(sources)
    # Allow these tokens in comments/docstrings; we check that they don't appear
    # as default branch fallbacks. Heuristic: no bare string literal of "main"/"master".
    for forbidden in ('"main"', "'main'", '"master"', "'master'"):
        assert forbidden not in src, f"sources.py contains hardcoded {forbidden}"


def test_resolve_default_branch_parses_symref(monkeypatch):
    """Default branch resolved from ls-remote --symref, NOT main/master fallback."""

    def fake(cmd, *a, **kw):
        return _make_completed(stdout="ref: refs/heads/develop\tHEAD\nabc123\tHEAD\n")

    monkeypatch.setattr(subprocess, "run", fake)
    assert sources._resolve_default_branch("file:///x") == "develop"


def test_resolve_default_branch_fails_when_no_symref(monkeypatch):
    def fake(cmd, *a, **kw):
        return _make_completed(stdout="garbage output")

    monkeypatch.setattr(subprocess, "run", fake)
    with pytest.raises(UpstreamCloneFailed):
        sources._resolve_default_branch("file:///x")


def test_shallow_clone_uses_depth_1(monkeypatch, tmp_path):
    calls = []

    def fake(cmd, *a, **kw):
        calls.append(cmd)
        return _make_completed(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake)
    sources._shallow_clone("file:///x", "main", tmp_path / "dest")
    assert any("--depth=1" in str(c) for c in calls), f"calls: {calls}"


def test_resolve_sha_returns_40_hex(monkeypatch, tmp_path):
    def fake(cmd, *a, **kw):
        return _make_completed(stdout="a" * 40 + "\n")

    monkeypatch.setattr(subprocess, "run", fake)
    sha = sources._resolve_sha(tmp_path)
    assert len(sha) == 40
    assert all(c in "0123456789abcdef" for c in sha)


def test_resolve_sha_rejects_invalid(monkeypatch, tmp_path):
    def fake(cmd, *a, **kw):
        return _make_completed(stdout="not-a-sha\n")

    monkeypatch.setattr(subprocess, "run", fake)
    with pytest.raises(UpstreamCloneFailed):
        sources._resolve_sha(tmp_path)


def test_clone_failure_raises(monkeypatch, tmp_path):
    def fake(cmd, *a, **kw):
        return _make_completed(returncode=128, stderr="clone failed")

    monkeypatch.setattr(subprocess, "run", fake)
    with pytest.raises(UpstreamCloneFailed):
        sources._shallow_clone("file:///x", "main", tmp_path / "dest")


def test_clean_working_tree_passes_when_empty(monkeypatch, tmp_path):
    def fake(cmd, *a, **kw):
        return _make_completed(stdout="")

    monkeypatch.setattr(subprocess, "run", fake)
    # Should not raise
    sources._verify_clean_working_tree(tmp_path)


def test_clean_working_tree_raises_when_dirty(monkeypatch, tmp_path):
    def fake(cmd, *a, **kw):
        return _make_completed(stdout=" M src/foo.py")

    monkeypatch.setattr(subprocess, "run", fake)
    with pytest.raises(RuntimeError, match="not clean"):
        sources._verify_clean_working_tree(tmp_path)


def test_clone_sources_records_resolved_sha(monkeypatch, tmp_path):
    """FR-2-A2 — resolved SHA is recorded regardless of whether ref: was overridden."""
    expected_sha = "b" * 40

    def fake(cmd, *a, **kw):
        if "ls-remote" in cmd:
            return _make_completed(stdout="ref: refs/heads/main\tHEAD\n")
        if "rev-parse" in cmd:
            return _make_completed(stdout=expected_sha + "\n")
        return _make_completed(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake)
    m = Manifest(
        schema_version="1",
        sources={"x": SourceSpec(id="x", url="file:///x")},
        imports=[],
        plugin=PluginSpec(name="p", description="d"),
        marketplace=MarketplaceSpec(name="m"),
        raw_sha256="0" * 64,
    )
    clones = sources.clone_sources(m, tmp_path)
    assert clones["x"].resolved_sha == expected_sha
    assert clones["x"].resolved_ref == "main"


def test_ref_and_sha_mutex(monkeypatch, tmp_path):
    """ref and sha fields are mutually exclusive on a SourceSpec."""
    m = Manifest(
        schema_version="1",
        sources={"x": SourceSpec(id="x", url="file:///x", ref="develop", sha="c" * 40)},
        imports=[],
        plugin=PluginSpec(name="p", description="d"),
        marketplace=MarketplaceSpec(name="m"),
        raw_sha256="0" * 64,
    )
    with pytest.raises(UpstreamCloneFailed, match="mutually exclusive"):
        sources.clone_sources(m, tmp_path)
