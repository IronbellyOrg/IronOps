"""YAML manifest parser and FR-1/FR-14/FR-15/FR-16 guard enforcement.

Per disposition D1 the manifest format is YAML and PyYAML is a runtime dep.
Per spec §5 the schema_version is the string ``"1"`` (not the int 1).
Per spec §11 ``hook-config`` and ``hook-script`` kinds are reserved in v0.1.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ironops.errors import ManifestInvalid, SelfOverwrite

# FR-16 — manifests MUST NOT redeclare generated paths
RESERVED_GENERATED_PATHS: frozenset[str] = frozenset(
    {".claude-plugin/plugin.json", "META.json", "THIRD_PARTY_LICENSES.md"}
)

# §11 — kinds reserved for future versions; v0.1 must reject
RESERVED_KINDS_V0_1: frozenset[str] = frozenset({"hook-config", "hook-script"})

_KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class SourceSpec:
    id: str
    url: str
    ref: str | None = None
    sha: str | None = None


@dataclass(frozen=True)
class ImportSpec:
    source: str
    from_path: str
    to: str
    kind: str
    requires: tuple[str, ...] = ()


@dataclass(frozen=True)
class PluginSpec:
    name: str
    description: str


@dataclass(frozen=True)
class MarketplaceSpec:
    name: str
    owner: dict[str, Any] = field(default_factory=dict)


@dataclass
class Manifest:
    schema_version: str
    sources: dict[str, SourceSpec]
    imports: list[ImportSpec]
    plugin: PluginSpec
    marketplace: MarketplaceSpec
    raw_sha256: str


def validate_schema_version(raw: Any) -> None:
    """FR-14 — schema_version MUST be the string ``"1"`` (not int, not dotted, not missing)."""
    if not isinstance(raw, str):
        raise ManifestInvalid(
            f"schema_version must be the string '1', got {type(raw).__name__}: {raw!r}"
        )
    if raw != "1":
        raise ManifestInvalid(
            f"schema_version must be the string '1', got {raw!r}"
        )


def validate_imports_non_empty(imports: Any) -> None:
    """FR-15 — imports key must be present and non-empty."""
    if imports is None:
        raise ManifestInvalid("imports key missing from manifest")
    if not isinstance(imports, list):
        raise ManifestInvalid(
            f"imports must be a list, got {type(imports).__name__}"
        )
    if len(imports) == 0:
        raise ManifestInvalid("imports list is empty")


def validate_no_self_overwrite(imports: list[ImportSpec]) -> None:
    """FR-16 — reject any import whose ``to:`` matches a RESERVED_GENERATED_PATHS entry."""
    for imp in imports:
        if imp.to in RESERVED_GENERATED_PATHS:
            raise SelfOverwrite(
                f"import would overwrite generated path {imp.to!r} "
                f"(reserved: {sorted(RESERVED_GENERATED_PATHS)})"
            )


def _parse_import(raw: dict[str, Any]) -> ImportSpec:
    for key in ("source", "from", "to", "kind"):
        if key not in raw:
            raise ManifestInvalid(f"import missing required key {key!r}: {raw!r}")
    kind = str(raw["kind"])
    if kind in RESERVED_KINDS_V0_1:
        raise ManifestInvalid(
            f"import uses reserved kind {kind!r} (v0.1 reserved: {sorted(RESERVED_KINDS_V0_1)})"
        )
    requires_raw = raw.get("requires", []) or []
    if not isinstance(requires_raw, list):
        raise ManifestInvalid(f"import.requires must be a list, got {requires_raw!r}")
    return ImportSpec(
        source=str(raw["source"]),
        from_path=str(raw["from"]),
        to=str(raw["to"]),
        kind=kind,
        requires=tuple(str(r) for r in requires_raw),
    )


def _parse_source(source_id: str, raw: dict[str, Any]) -> SourceSpec:
    if "url" not in raw:
        raise ManifestInvalid(f"source {source_id!r} missing required key 'url'")
    return SourceSpec(
        id=source_id,
        url=str(raw["url"]),
        ref=raw.get("ref"),
        sha=raw.get("sha"),
    )


def _parse_plugin(raw: Any) -> PluginSpec:
    if not isinstance(raw, dict):
        raise ManifestInvalid("plugin block must be a mapping")
    for key in ("name", "description"):
        if key not in raw:
            raise ManifestInvalid(f"plugin block missing required key {key!r}")
    name = str(raw["name"])
    if not _KEBAB_RE.match(name):
        raise ManifestInvalid(
            f"plugin.name {name!r} must be kebab-case (lowercase letters/digits separated by single hyphens)"
        )
    return PluginSpec(name=name, description=str(raw["description"]))


def _parse_marketplace(raw: Any) -> MarketplaceSpec:
    if not isinstance(raw, dict):
        raise ManifestInvalid("marketplace block must be a mapping")
    if "name" not in raw:
        raise ManifestInvalid("marketplace block missing required key 'name'")
    return MarketplaceSpec(name=str(raw["name"]), owner=dict(raw.get("owner") or {}))


def load_manifest(path: Path) -> Manifest:
    """Parse a manifest YAML file and enforce FR-1/14/15/16 guards.

    Returns a fully-validated Manifest with ``raw_sha256`` computed over
    the file bytes (used by metadata.write_meta_json).
    """
    path = Path(path)
    if not path.exists():
        raise ManifestInvalid(f"manifest file not found: {path}")
    raw_bytes = path.read_bytes()
    raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    try:
        data = yaml.safe_load(raw_bytes)
    except yaml.YAMLError as exc:
        raise ManifestInvalid(f"manifest YAML parse error: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestInvalid("manifest must be a top-level mapping")

    validate_schema_version(data.get("schema_version"))

    sources_raw = data.get("sources") or {}
    if not isinstance(sources_raw, dict) or not sources_raw:
        raise ManifestInvalid("sources block must be a non-empty mapping")
    sources = {
        sid: _parse_source(sid, sraw) for sid, sraw in sources_raw.items()
    }

    validate_imports_non_empty(data.get("imports"))
    imports = [_parse_import(raw) for raw in data["imports"]]

    # FR-1 — each import.source must reference a declared source id
    for imp in imports:
        if imp.source not in sources:
            raise ManifestInvalid(
                f"import references unknown source id {imp.source!r}"
            )

    validate_no_self_overwrite(imports)

    plugin = _parse_plugin(data.get("plugin"))
    marketplace = _parse_marketplace(data.get("marketplace"))

    return Manifest(
        schema_version=data["schema_version"],
        sources=sources,
        imports=imports,
        plugin=plugin,
        marketplace=marketplace,
        raw_sha256=raw_sha256,
    )
