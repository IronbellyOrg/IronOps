# Changelog

All notable changes to IronOps will be documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

(no changes yet)

## [0.1.0] — 2026-05-28 — initial release

### Added

- Greenfield Python package `src/ironops/` (errors, manifest, sources, render,
  metadata, validate, publish, pipeline, cli).
- YAML manifest format with `schema_version: "1"` (FR-14).
- 9 NFR-7 categorical exit codes:
  `MANIFEST_INVALID`, `UNRESOLVED_IMPORT`, `CO_IMPORT_MISSING`,
  `VALIDATE_FAILED`, `PATH_ESCAPE`, `UPSTREAM_CLONE_FAILED`,
  `SELF_OVERWRITE`, `BUILDER_DIRTY_TREE`, `PUBLISH_FAILED`.
- 8-stage build pipeline (PREFLIGHT → CLONE → READ MANIFEST → RENDER →
  WRITE METADATA → VALIDATE → PUBLISH → REPORT).
- FR-1 through FR-16 implemented and tested.
- AC-1 through AC-10 verified.
- v0.1 production manifest at `manifest.yaml` aggregating 11 agents + 10
  skill directories + 7 commands from IronClaude.
- GitHub Actions workflows: `test.yml` (matrix Py 3.10/3.11/3.12) and
  `build-publish.yml` (UC-1 — push + scheduled + workflow_dispatch with
  concurrency guard).

### Spec amendments

- **SPEC §NFR-7** — added `PUBLISH_FAILED` as 9th categorical code
  (disposition D3).
- **SPEC §2.1 + §17 Definitions** — builder lives in `src/ironops/`
  as a Python package (not `scripts/build_plugin.py`) (disposition D4).

### Deferred

- `prd` skill — commented out in v0.1 manifest, deferred to v0.2 (OQ-6).
