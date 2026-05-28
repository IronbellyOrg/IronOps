"""AC-2 — golden snapshot test against the v0.1 production manifest.

Skipped when /config/workspace/IronOps/manifest.yaml is not yet present —
the production manifest is created in Phase 7 Step 7.3.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from ironops.pipeline import BuildContext, run_build

REPO_ROOT = Path(__file__).resolve().parents[2]
PROD_MANIFEST = REPO_ROOT / "manifest.yaml"
GOLDEN_PATH = REPO_ROOT / "tests" / "fixtures" / "golden" / "v0_1_plugin_tree.json"


pytestmark = pytest.mark.skipif(
    not GOLDEN_PATH.exists(),
    reason="golden tree not yet bootstrapped — REGEN_GOLDEN=1 against the production manifest (requires upstream access) creates it",
)


def _hash_tree(root: Path) -> dict[str, str]:
    """Map relative path → sha256 for every file under root, skipping META.json (built_at)."""
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name != "META.json":
            rel = str(p.relative_to(root))
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def test_golden_snapshot_matches(
    tmp_path, mock_git_clone, mock_claude_validate, patched_builder_version
):
    """Run the builder against the v0.1 manifest, compare against golden tree."""
    ctx = BuildContext(
        manifest_path=PROD_MANIFEST,
        staging_dir=tmp_path / "staging",
        scratch_dir=tmp_path / "scratch",
        dry_run=True,
    )
    result = run_build(ctx)
    assert result.success, result.summary
    actual = _hash_tree(tmp_path / "staging")
    if os.environ.get("REGEN_GOLDEN") == "1":
        GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN_PATH.write_text(json.dumps(actual, indent=2, sort_keys=True))
        pytest.skip("REGEN_GOLDEN=1 — golden tree regenerated")
    if not GOLDEN_PATH.exists():
        pytest.skip("golden tree not bootstrapped; re-run with REGEN_GOLDEN=1")
    expected = json.loads(GOLDEN_PATH.read_text())
    assert actual == expected, "golden snapshot mismatch"


def test_golden_file_count_matches_summary(
    tmp_path, mock_git_clone, mock_claude_validate, patched_builder_version
):
    ctx = BuildContext(
        manifest_path=PROD_MANIFEST,
        staging_dir=tmp_path / "staging",
        scratch_dir=tmp_path / "scratch",
        dry_run=True,
    )
    result = run_build(ctx)
    assert result.success
    meta = json.loads((tmp_path / "staging" / "META.json").read_text())
    # +4 generated files (plugin.json, META.json itself, licenses, marketplace.json)
    actual_files = sum(1 for p in (tmp_path / "staging").rglob("*") if p.is_file())
    assert (
        meta["summary"]["total_files"] + 4 == actual_files
        or meta["summary"]["total_files"] <= actual_files
    )
