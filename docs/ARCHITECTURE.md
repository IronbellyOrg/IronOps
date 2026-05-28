# IronOps Architecture

IronOps is a build-time aggregator that consumes a YAML manifest declaring
upstream sources and per-source file allowlists, then assembles a curated
Claude Code plugin tree and publishes it atomically to a private GitHub
marketplace repo.

## Pipeline: 8 stages

The builder executes 8 stages in strict order (see SPEC §7):

```
0. PREFLIGHT      verify tooling, resolve builder version, enforce clean-tree (FR-12)
1. CLONE          shallow-clone each declared upstream at resolved HEAD (FR-2)
2. READ MANIFEST  parse + validate (FR-1/14/15/16)
3. RENDER         copy imports into staging, enforce co-imports (FR-4) + path safety (FR-8)
4. WRITE METADATA emit plugin.json, META.json, THIRD_PARTY_LICENSES.md, marketplace.json
5. VALIDATE       run `claude plugin validate` against staging (FR-5)
6. PUBLISH        rsync + git commit/push atomically (FR-9)
7. REPORT         emit stdout summary with counts + SHAs
```

Stage 2 (READ MANIFEST) is necessarily executed at the *start* of Stage 1
since the clone loop iterates `sources[*]` declared in the manifest. The
spec's stage numbering is the canonical naming; the runtime ordering puts
parsing before cloning so Stage 1 has a manifest to iterate.

## Module → stage mapping

| Stage | Primary module(s) |
|---|---|
| 0 PREFLIGHT | `pipeline._stage_0_preflight` + `metadata._resolve_builder_version` |
| 1 CLONE | `sources.clone_sources` |
| 2 READ MANIFEST | `manifest.load_manifest` |
| 3 RENDER | `render.render_to_staging` + `render.enforce_co_imports` + `render.enforce_path_safety` |
| 4 WRITE METADATA | `metadata.write_plugin_json` + `write_meta_json` + `write_third_party_licenses` + `write_marketplace_json` |
| 5 VALIDATE | `validate.run_validator` |
| 6 PUBLISH | `publish.publish_to_marketplace` |
| 7 REPORT | `pipeline._stage_7_report` |

## Where things live

- `src/ironops/` — Python package (errors, manifest, sources, render, metadata, validate, publish, pipeline, cli).
- `tests/` — pytest suite (unit, integration, cli) + hermetic fixtures.
- `manifest.yaml` — v0.1 production manifest at the repo root.
- `.github/workflows/` — CI (`test.yml`) + UC-1 publish (`build-publish.yml`).
- `docs/` — this file, `MANIFEST_AUTHORING.md`, `MARKETPLACE_BOOTSTRAP.md`, `CHANGELOG.md`.

## FR/NFR/AC reference

For authoritative requirement detail, see
[`.dev/releases/1.0/0.1/SPEC_IRONOPS_DEVOPS_PLUGIN.md`](../.dev/releases/1.0/0.1/SPEC_IRONOPS_DEVOPS_PLUGIN.md).
