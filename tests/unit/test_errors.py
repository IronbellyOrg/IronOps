"""Unit tests for ironops.errors — ExitCode enum + BuilderError subclasses."""

from __future__ import annotations

import pytest

from ironops.errors import (
    BuilderDirtyTree,
    BuilderError,
    CoImportMissing,
    ExitCode,
    ManifestInvalid,
    PathEscape,
    PublishFailed,
    SelfOverwrite,
    UnresolvedImport,
    UpstreamCloneFailed,
    ValidateFailed,
    format_failure,
)

NFR7_CASES = [
    pytest.param("MANIFEST_INVALID", 10, ManifestInvalid, id="MANIFEST_INVALID"),
    pytest.param("UNRESOLVED_IMPORT", 11, UnresolvedImport, id="UNRESOLVED_IMPORT"),
    pytest.param("CO_IMPORT_MISSING", 12, CoImportMissing, id="CO_IMPORT_MISSING"),
    pytest.param("VALIDATE_FAILED", 13, ValidateFailed, id="VALIDATE_FAILED"),
    pytest.param("PATH_ESCAPE", 14, PathEscape, id="PATH_ESCAPE"),
    pytest.param("UPSTREAM_CLONE_FAILED", 15, UpstreamCloneFailed, id="UPSTREAM_CLONE_FAILED"),
    pytest.param("SELF_OVERWRITE", 16, SelfOverwrite, id="SELF_OVERWRITE"),
    pytest.param("BUILDER_DIRTY_TREE", 17, BuilderDirtyTree, id="BUILDER_DIRTY_TREE"),
    pytest.param("PUBLISH_FAILED", 18, PublishFailed, id="PUBLISH_FAILED"),
]


def test_exit_code_enum_values_distinct():
    """Every NFR-7 categorical code must have a distinct integer."""
    values = [c.value for c in ExitCode]
    assert len(values) == len(set(values)), "ExitCode integer values must be distinct"


@pytest.mark.parametrize("code_name,code_int,subclass", NFR7_CASES)
def test_builder_error_subclasses_set_code(code_name, code_int, subclass):
    """Each subclass must set its `code` to the matching ExitCode."""
    inst = subclass(f"test {code_name}")
    assert isinstance(inst, BuilderError)
    assert inst.code == ExitCode[code_name]
    assert int(inst.code) == code_int


@pytest.mark.parametrize("code_name,code_int,subclass", NFR7_CASES)
def test_format_failure_single_line(code_name, code_int, subclass):
    """NFR-7 part (a) — one-line stderr summary; no embedded newlines."""
    err = subclass(f"multi\nline\nsummary for {code_name}")
    out = format_failure(err)
    assert "\n" not in out
    assert "\r" not in out


@pytest.mark.parametrize("code_name,code_int,subclass", NFR7_CASES)
def test_format_failure_includes_code_string(code_name, code_int, subclass):
    """Format output must include the code name for grep-friendly CI logs."""
    err = subclass(f"summary for {code_name}")
    out = format_failure(err)
    assert code_name in out
    assert "summary for" in out
