---
id: "IRONOPS-DEVOPS-PLUGIN-v0.1-SPEC"
title: "IronOps DevOps Claude Plugin — v0.1 Implementation Specification"
spec_type: "feature-release"
target_release: "v0.1"
status: "🟡 Draft — spec-panel reviewed"
created_date: "2026-05-27"
updated_date: "2026-05-27"
parent_doc: ".dev/tasks/to-do/TASK-RESEARCH-20260527-150111-ironops-plugin-aggregator/DECISION-BRIEF-ironops-aggregator.md"
authors: ["RyanW", "spec-panel/discussion"]
review_panel: ["wiegers", "adzic", "cockburn", "fowler", "nygard", "whittaker", "newman", "hohpe", "crispin", "gregory", "hightower"]
focus_areas: ["requirements", "architecture", "correctness"]
upstream_repo: "git@github.com:IronbellyOrg/IronClaude.git"
distribution_repo: "git@github.com:IronbellyOrg/ironops-marketplace.git"
---

# IronOps DevOps Claude Plugin — v0.1 Implementation Specification

> **What this document is:** An implementation-ready specification for v0.1 of `ironops-devops`, a curated Claude Code plugin built at CI time by aggregating allowlisted files from IronClaude (and future upstreams) into a single distributable plugin published through a private GitHub marketplace.
>
> **What this document is NOT:** A PRD, a TDD, or a tasklist. The PRD layer is intentionally skipped per user direction. The next downstream artifact is an MDTM task file produced by `/task-builder`, which converts these FRs/NFRs into checklist items.

---

## 1. Actors and Primary Use Cases

| Actor | Goal | Trigger |
|---|---|---|
| **A1 — Builder CI** | Produce a validated `ironops-devops` plugin tree and publish it to the marketplace repo, recording provenance. | Push to IronOps `main`, scheduled rebuild, or manual workflow_dispatch |
| **A2 — Plugin author / release engineer** | Edit `manifest.yaml` to add/remove curated components without forking upstream. | New IronClaude release, scope adjustment |
| **A3 — Target-project developer** | Install one plugin (`/plugin install ironops-devops@ironops`) and invoke curated DevOps skills. | Onboarding a new infra repo |

### UC-1 — Build and publish (A1)

**Primary:** Builder CI. **Goal:** rendered + validated + published plugin. **Trigger:** push to IronOps `main`.
**Main success scenario:** Clone upstreams at HEAD → render plugin tree per `manifest.yaml` → write `META.json` → run `claude plugin validate` → rsync into marketplace repo → push.

### UC-2 — Curate scope (A2)

**Primary:** Release engineer. **Goal:** add/remove a curated component. **Trigger:** decision to include `new-skill`. **Main success scenario:** edit `manifest.yaml`, push, CI builds, marketplace updates.

### UC-3 — Install and use (A3)

**Primary:** Target-project developer. **Goal:** access curated DevOps skills. **Main success scenario:** `claude plugin marketplace add IronbellyOrg/ironops-marketplace` → `claude plugin install ironops-devops@ironops` → `/ironops-devops:troubleshoot` is callable.

---

## 2. Scope

### 2.1 In Scope for v0.1

- A YAML manifest (`manifest.yaml`) declaring upstream sources and per-source file/directory allowlists.
- A Python-based builder packaged as `src/ironops/` (installable via `uv pip install -e .`, entry point `ironops` CLI; `scripts/` reserved for future helper scripts only — per gap-fill disposition **D4** in `research/05-gap-fill-disposition.md`) that consumes the manifest and produces a `dist/plugins/ironops-devops/` tree.
- Rendered Claude Code plugin components: `agents/`, `skills/`, `commands/`, `plugin.json`, `META.json`, `THIRD_PARTY_LICENSES.md`.
- Generation of `.claude-plugin/marketplace.json` for the marketplace repo, listing the single `ironops-devops` plugin.
- Validation gate: `claude plugin validate` must exit zero before publish.
- Co-import enforcement: a command that references `Skill sc:<x>-protocol` must be co-imported with that skill (or the build fails).
- Path-safety enforcement: all rewritten paths must resolve inside the plugin root.
- GitHub Actions workflow that runs the builder on push to `main` and on manual dispatch, then rsyncs into the marketplace repo and pushes.
- Provenance: `META.json` with source repo, commit SHA, and per-file source paths.
- Test fixtures: golden-output snapshot of the rendered plugin tree for the v0.1 manifest; CI test matrix with malformed manifests.

### 2.2 Out of Scope for v0.1

- `hooks/hooks.json` and hook scripts (designed, not shipped — see §11).
- `.mcp.json` and MCP server bundling.
- `monitors/`, `themes/`, `output-styles/`, `bin/`, `.lsp.json`.
- Replacing or shipping project-level `CLAUDE.md`/`RULES.md`/`PRINCIPLES.md` (no plugin slot).
- Semver-pinned `plugin.json.version` (v0.1 uses commit-SHA mode).
- Plugin dependencies (`dependencies` field) — single plugin, no inter-plugin deps yet.
- Public marketplace publication.
- Airgap seeding (`CLAUDE_CODE_PLUGIN_SEED_DIR`) — design noted, deferred.
- Multi-track parallel builds across multiple plugins.
- User-facing onboarding/doctor commands within the plugin.

### 2.3 Explicit Non-Decisions

- **Builder language:** Python 3.11+ recommended (matches IronClaude tooling). Not a hard requirement.
- **Whether the marketplace repo is the same repo as the builder:** v0.1 assumes **separate** — IronOps holds the builder; `IronbellyOrg/ironops-marketplace` holds the published artifacts.

---

## 3. Functional Requirements

Each FR has measurable acceptance criteria. Severity classifications (CRITICAL / MAJOR / MINOR) reflect impact on v0.1 release readiness.

### FR-1 — Manifest-driven aggregation [CRITICAL]

The builder MUST read a single `manifest.yaml` declaring sources and imports; it MUST NOT hard-code any upstream file path.

**Acceptance:**
- A1: Given `manifest.yaml` with N entries, builder copies exactly N files/dirs (or fails on any unresolved entry).
- A2: Removing an entry from `manifest.yaml` and rebuilding produces a plugin without that component.
- A3: Builder rejects manifests with `imports: []` or missing top-level `sources`/`imports` with exit code ≠ 0.

### FR-2 — Always-latest mainline at build time [CRITICAL]

The builder MUST clone each declared source at the source's default branch HEAD at build invocation time, unless the manifest entry explicitly overrides with `ref:` or `sha:`.

**Acceptance:**
- A1: Two consecutive builds where upstream has new commits between them produce different `META.json` SHAs.
- A2: Builder records the resolved commit SHA for every source, regardless of whether `ref:` was specified.
- A3: Builder MUST resolve the upstream's default branch programmatically (`git remote show` or equivalent); MUST NOT assume `main` or `master`. [Whittaker — Divergence Attack closure]

### FR-3 — Read-only upstream consumption [CRITICAL]

The builder MUST NOT modify, patch, or write to the upstream clone. All transformations happen on the destination tree.

**Acceptance:**
- A1: After build, `git -C <upstream-clone> status` reports clean working tree.
- A2: Any content rewriting (e.g., path canonicalization) operates on the destination file, not the source.

### FR-4 — Co-import enforcement [CRITICAL]

If a copied command file references `Skill sc:<x>-protocol`, the skill `sc-<x>-protocol/` (or `<x>-protocol/` post-rename per FR-7) MUST also be copied. Builder fails the build if the referenced skill is not in the manifest.

**Acceptance:**
- A1: Manifest including `commands/troubleshoot.md` without `skills/sc-troubleshoot-protocol/` causes a build failure with a non-zero exit code and a message naming both the unimported skill and the citing command file.
- A2: Reverse direction (skill imported without dependent command) is allowed and warned, not failed.

### FR-5 — Validation gate [CRITICAL]

The builder MUST invoke `claude plugin validate` against the rendered plugin tree; non-zero exit MUST abort publish.

**Acceptance:**
- A1: Given a deliberately broken rendered plugin (e.g., malformed `plugin.json`), CI publish step does not run.
- A2: Validator output is captured to a build log artifact.

### FR-6 — Provenance via META.json [CRITICAL]

The builder MUST write `META.json` at the plugin root with the schema in §6.

**Acceptance:**
- A1: Every file in the rendered plugin tree has a corresponding `sources[].manifest_paths` entry recording origin.
- A2: `META.json` contains a `built_at` ISO-8601 UTC timestamp and `builder_version` string (git SHA of IronOps at build time).

### FR-7 — Plugin namespace [MAJOR]

The plugin name MUST be `ironops-devops`. Skill files MUST be copied unchanged (no `sc:` namespace rewriting); namespacing is provided by Claude Code via the plugin name. Skill directory names with a leading `sc-` prefix (IronClaude convention) MAY be renamed to drop the prefix in the rendered plugin (deferred — v0.1 keeps original names).

**Acceptance:**
- A1: `claude plugin install ironops-devops@ironops` exposes skills as `/ironops-devops:<skill-name>`.
- A2: No file content under `agents/` or `skills/<name>/SKILL.md` has been textually modified relative to the upstream source (verified by byte-for-byte comparison of body, excluding frontmatter normalization if any).

### FR-8 — Path safety [CRITICAL]

Every reference inside a copied file that uses a relative or absolute path MUST be inspected. References to files outside the rendered plugin root MUST cause a build failure with a clear message; references to `${CLAUDE_PLUGIN_ROOT}/...` paths are allowed.

**Acceptance:**
- A1: An imported skill containing `Read /config/workspace/IronClaude/...` causes a build failure.
- A2: An imported hook script (when re-enabled in a later release) containing `${CLAUDE_PLUGIN_ROOT}/scripts/foo.sh` passes validation.

### FR-9 — Atomic publish [MAJOR]

Publish to the marketplace repo MUST be all-or-nothing. A failed validate, a half-written `META.json`, or a partial copy MUST NOT result in a pushed commit. [Whittaker — Sequence Attack closure]

**Acceptance:**
- A1: Builder writes the rendered plugin to a staging directory, validates there, then `rsync --delete` into the marketplace repo only after validation succeeds.
- A2: If any pipeline stage (clone, copy, render, validate, write META) fails, marketplace repo HEAD is unchanged.

### FR-10 — Marketplace manifest generation [MAJOR]

The builder MUST emit `.claude-plugin/marketplace.json` listing the `ironops-devops` plugin with `source: "./plugins/ironops-devops"`.

**Acceptance:**
- A1: `claude plugin marketplace add ./marketplace-repo && claude plugin install ironops-devops@ironops` succeeds end-to-end against a freshly built marketplace.

### FR-11 — Third-party license attribution [MAJOR]

The builder MUST emit `THIRD_PARTY_LICENSES.md` inside the plugin enumerating each upstream source repo, its license, and a per-file mapping (or per-directory mapping for skills).

**Acceptance:**
- A1: Inspecting the rendered plugin shows `THIRD_PARTY_LICENSES.md`; the file references at least the upstream IronClaude license and lists each imported source file or directory.

### FR-12 — Deterministic, headless operation [MAJOR]

The builder MUST run non-interactively, MUST be deterministic given identical inputs (same manifest, same upstream SHAs), and MUST exit with meaningful codes (0 = success, ≠0 = failure with stderr explanation). [Hightower closure]

**Acceptance:**
- A1: Two builder invocations with the same `manifest.yaml` and pinned upstream SHAs produce byte-identical rendered plugin trees (excluding `META.json.built_at`).
- A2: Builder accepts no interactive input on stdin.

### FR-13 — Versioning strategy v0.1 [MINOR]

The rendered `plugin.json` MUST omit `version`. Updates are driven by the commit SHA of the marketplace repo.

**Acceptance:**
- A1: `plugin.json` written by builder contains no `version` key.
- A2: A documented migration path to explicit semver exists in §11 for v0.2+.

### FR-14 — Manifest schema versioning [MAJOR] [Newman closure]

The manifest MUST declare a top-level `schema_version: "1"` field. Builder rejects unknown schema versions with a clear "upgrade required" error and warns (does not fail) on deprecated keys.

**Acceptance:**
- A1: Manifest with `schema_version: "999"` is rejected.
- A2: Manifest missing `schema_version` is rejected.

### FR-15 — Reject empty manifests [MAJOR] [Whittaker — Zero/Empty Attack closure]

`imports: []` or missing `imports:` MUST fail the build with exit code ≠ 0.

**Acceptance:**
- A1: A manifest with `sources: [...]` and `imports: []` fails with a message naming the offending section.

### FR-16 — Block self-overwrite via manifest [MAJOR] [Whittaker — Sentinel Collision closure]

The manifest MUST NOT be allowed to declare an `import` whose destination is `.claude-plugin/plugin.json`, `META.json`, `THIRD_PARTY_LICENSES.md`, or any file the builder generates. The builder owns those paths.

**Acceptance:**
- A1: A manifest entry targeting `.claude-plugin/plugin.json` causes build failure.

---

## 4. Non-Functional Requirements

### NFR-1 — Reproducibility

Given pinned upstream SHAs in the manifest (or recorded in `META.json`), the builder MUST produce a byte-identical plugin tree on any compliant runner (Linux x86_64, Python 3.11+, git, rsync). `META.json.built_at` is the only permitted source of non-determinism.

### NFR-2 — Build wall-clock budget

A full build (clone, render, validate, stage) on a clean CI runner SHOULD complete in under 60 seconds for the v0.1 manifest (~26 component imports). HARD ceiling: 5 minutes. Exceeding the ceiling fails the build.

### NFR-3 — Plugin context cost budget [Whittaker — Accumulation Attack closure]

The rendered plugin MUST report its per-session always-on token cost as part of the build summary (`claude plugin details ironops-devops` after install gives this). v0.1 target: < 500 tokens always-on. Exceeding 1500 tokens always-on requires release-engineer override (manual approval, not build-time gate).

### NFR-4 — Plugin validity

The rendered plugin MUST pass `claude plugin validate` with zero errors and zero warnings before publish.

### NFR-5 — Security: no executable code from upstream is invoked at build time

The builder MUST NOT `exec` upstream-supplied shell scripts during build, even if they appear in the manifest. v0.1 builder copies files only; it does not run them.

### NFR-6 — Auditability

Every published commit on the marketplace repo MUST contain a `META.json` whose `sources[].sha` values match the upstream repo's actual SHAs (manually verifiable by re-cloning at those SHAs).

### NFR-7 — Failure transparency

Build failures MUST emit (a) a one-line stderr summary, (b) one of the 9 categorical failure codes — `MANIFEST_INVALID`, `UNRESOLVED_IMPORT`, `CO_IMPORT_MISSING`, `VALIDATE_FAILED`, `PATH_ESCAPE`, `UPSTREAM_CLONE_FAILED`, `SELF_OVERWRITE`, `BUILDER_DIRTY_TREE`, `PUBLISH_FAILED` — and (c) a full log artifact retained for 30 days.

The `PUBLISH_FAILED` code (added per gap-fill disposition **D3** in `research/05-gap-fill-disposition.md`) covers rsync or `git add/commit/push` failures during Stage 6 publish that do not map cleanly to the prior 8 categorical codes; these failures previously had no distinct categorical label, so D3 mandates this 9th code as a deliberate, documented spec evolution rather than a silent extension. `BUILDER_DIRTY_TREE` (already referenced in §9 guard table at Stage 0 / FR-12) is included explicitly here for completeness of the enumeration.

### NFR-8 — Backwards-compat for manifest schema

A manifest authored against `schema_version: "1"` MUST continue to build successfully through all v0.x releases. Schema breaking changes are reserved for explicit major bumps documented in `CHANGELOG.md`.

### NFR-9 — Read-only upstream working trees

After every build, `git -C <upstream-clone> status` MUST report a clean working tree. (Reinforces FR-3 as a measurable runtime invariant.)

---

## 5. Manifest Schema Requirements (sketch — TDD-level refinement deferred)

```yaml
# manifest.yaml
schema_version: "1"

sources:
  ironclaude:
    url: "git@github.com:IronbellyOrg/IronClaude.git"
    # ref: optional — defaults to upstream's default branch HEAD at build time
    # sha: optional — pins to an exact commit; mutually exclusive with ref

imports:
  - source: ironclaude
    from: "src/superclaude/agents/devops-architect.md"
    to: "agents/devops-architect.md"
    kind: agent

  - source: ironclaude
    from: "src/superclaude/skills/sc-troubleshoot-protocol/"
    to: "skills/sc-troubleshoot-protocol/"
    kind: skill

  - source: ironclaude
    from: "src/superclaude/commands/troubleshoot.md"
    to: "commands/troubleshoot.md"
    kind: command
    requires: ["skills/sc-troubleshoot-protocol/"]   # explicit co-import dependency

plugin:
  name: "ironops-devops"
  description: "Curated DevOps / SRE / CI-CD toolkit for Claude Code"
  # version: intentionally omitted — see FR-13

marketplace:
  name: "ironops"
  owner: { name: "Ironbelly", email: "ops@example.invalid" }
```

**Schema requirements (not the full schema — that goes in implementation):**

- `schema_version` required, string, currently `"1"`.
- `sources` required, non-empty map.
- `imports` required, non-empty array.
- Each import: `source` (must reference a key in `sources`), `from` (path inside the upstream), `to` (path inside the rendered plugin), `kind` (one of: `agent`, `skill`, `command`, `template`, `script`, `other`).
- `requires` optional array of plugin-internal `to` paths that must also be imported.
- `plugin.name` required, kebab-case.
- `marketplace.name` required, kebab-case, MUST NOT match an Anthropic-reserved name.

---

## 6. META.json Schema [Hohpe closure — explicit integration contract]

```json
{
  "schema_version": "1",
  "plugin_name": "ironops-devops",
  "built_at": "2026-05-27T14:51:13Z",
  "builder_version": "<IronOps git SHA at build time>",
  "manifest_sha256": "<sha256 of manifest.yaml at build time>",
  "sources": [
    {
      "id": "ironclaude",
      "repo": "git@github.com:IronbellyOrg/IronClaude.git",
      "ref": "main",
      "resolved_sha": "<40-char commit SHA>",
      "imports": [
        { "from": "src/superclaude/agents/devops-architect.md", "to": "agents/devops-architect.md", "kind": "agent" }
      ]
    }
  ],
  "summary": {
    "agent_count": 11,
    "skill_count": 8,
    "command_count": 7,
    "total_files": 26
  }
}
```

Schema requirements as in §5: `schema_version` mandatory; future schema changes go via explicit major bump.

---

## 7. Build/Publish Pipeline (canonical ordering — FR-9 enforces atomicity)

```
Stage 0: PREFLIGHT
  - verify python3.11+, git, rsync available
  - verify dirty=false on IronOps working tree (FR-12 determinism)

Stage 1: CLONE
  - for each `sources[*]`: shallow clone to a scratch dir
  - if `ref:` unset, resolve default branch via `git remote show`
  - record resolved SHA per source

Stage 2: READ MANIFEST
  - parse manifest.yaml
  - reject schema_version != "1"   (FR-14)
  - reject empty imports           (FR-15)
  - reject self-overwrite targets  (FR-16)

Stage 3: RENDER (to staging dir, never directly into marketplace repo)
  - for each import: copy from upstream clone to staging dir
  - rewrite any cross-plugin-root references; reject path escapes (FR-8)
  - enforce co-import requirements (FR-4)

Stage 4: WRITE METADATA
  - emit plugin.json (no `version` key — FR-13)
  - emit META.json (FR-6, §6 schema)
  - emit THIRD_PARTY_LICENSES.md (FR-11)
  - emit ../.claude-plugin/marketplace.json (FR-10)

Stage 5: VALIDATE
  - run `claude plugin validate` against staging dir (FR-5)
  - on failure: STOP, exit ≠0, marketplace repo unchanged

Stage 6: PUBLISH (atomic)
  - rsync --delete staging-dir -> marketplace-repo/plugins/ironops-devops/
  - git add, commit with provenance message including resolved SHA, push to main
  - on push failure: leave working tree as-is, exit ≠0

Stage 7: REPORT
  - emit build summary to stdout (counts, SHAs, validator output, push status)
```

---

## 8. State Variable Registry [correctness focus — mandatory]

| Variable | Type | Initial Value | Invariant | Read Operations | Write Operations |
|---|---|---|---|---|---|
| `manifest` | parsed YAML object | unset | `schema_version == "1"`; `imports` non-empty; no self-overwrite targets | Stage 3, 4, 7 | Stage 2 only |
| `upstream_clones[src_id]` | path to clone | unset | clean working tree after every read; never modified by builder (FR-3, NFR-9) | Stage 3 | Stage 1 only |
| `resolved_shas[src_id]` | 40-char string | unset | matches the actual `git rev-parse HEAD` of the corresponding upstream clone | Stage 4 (META.json), Stage 6 (commit message), Stage 7 | Stage 1 only |
| `staging_dir` | path | empty dir at Stage 0 start | only mutated by builder; contents replaceable across builds | Stage 5, 6 | Stages 3, 4 |
| `validator_exit_code` | int | unset | gate: must equal 0 before Stage 6 begins (FR-5, FR-9) | Stage 6 (decision), Stage 7 (report) | Stage 5 only |
| `marketplace_repo_head` | git SHA | upstream HEAD pre-build | only advances after successful validate (FR-9 atomicity) | Stage 0 (precondition log), Stage 7 | Stage 6 only |
| `enabled_target` (downstream) | bool per scope | false | only `true` after `/plugin install` (target-side concern; not builder state) | n/a | Claude Code, not builder |

---

## 9. Guard Condition Boundary Table [mandatory under correctness focus]

| Guard | Location | Input Condition | Variable Value | Guard Result | Specified Behavior | Status |
|---|---|---|---|---|---|---|
| `schema_version == "1"` | Stage 2 (FR-14) | Zero/Empty | `null`, missing | false | Reject; exit ≠0 `MANIFEST_INVALID` | OK |
| `schema_version == "1"` | Stage 2 (FR-14) | One/Minimal | `"1"` | true | Proceed | OK |
| `schema_version == "1"` | Stage 2 (FR-14) | Typical | `"1"` | true | Proceed | OK |
| `schema_version == "1"` | Stage 2 (FR-14) | Maximum/Overflow | `"999"` | false | Reject; "upgrade builder" | OK |
| `schema_version == "1"` | Stage 2 (FR-14) | Sentinel Match | `"1.0"`, `"1.x"` | false | Reject; require exact `"1"` | OK |
| `schema_version == "1"` | Stage 2 (FR-14) | Legitimate Edge Case | `1` (int, not str) | false | Reject; require string `"1"` | OK |
| `imports non-empty` | Stage 2 (FR-15) | Zero/Empty | `[]` or missing | false | Reject; exit ≠0 `MANIFEST_INVALID` | OK |
| `imports non-empty` | Stage 2 (FR-15) | One/Minimal | `[<one entry>]` | true | Proceed (degenerate but legal) | OK |
| `imports non-empty` | Stage 2 (FR-15) | Typical | ~26 entries | true | Proceed | OK |
| `imports non-empty` | Stage 2 (FR-15) | Maximum/Overflow | 10000 entries | true | Proceed but warn if rendered plugin > NFR-3 context budget | OK |
| `imports non-empty` | Stage 2 (FR-15) | Sentinel Match | n/a | n/a | n/a | OK |
| `import.to not self-overwrite` | Stage 2 (FR-16) | Sentinel Match | `to: ".claude-plugin/plugin.json"` | false | Reject; exit ≠0 `SELF_OVERWRITE` | OK |
| `import.to not self-overwrite` | Stage 2 (FR-16) | Sentinel Match | `to: "META.json"` | false | Reject; exit ≠0 `SELF_OVERWRITE` | OK |
| `import.to not self-overwrite` | Stage 2 (FR-16) | Typical | `to: "agents/foo.md"` | true | Proceed | OK |
| `co-import satisfied` | Stage 3 (FR-4) | Zero/Empty | command without companion skill | false | Reject; exit ≠0 `CO_IMPORT_MISSING` | OK |
| `co-import satisfied` | Stage 3 (FR-4) | Typical | command + skill both present | true | Proceed | OK |
| `co-import satisfied` | Stage 3 (FR-4) | Legitimate Edge | skill imported without companion command | true (with warning) | Proceed; emit warning | OK |
| `path inside plugin root` | Stage 3 (FR-8) | Sentinel Match | `../../etc/passwd` | false | Reject; exit ≠0 `PATH_ESCAPE` | OK |
| `path inside plugin root` | Stage 3 (FR-8) | Typical | `./scripts/x.sh` | true | Proceed | OK |
| `path inside plugin root` | Stage 3 (FR-8) | Legitimate Edge | `${CLAUDE_PLUGIN_ROOT}/scripts/x.sh` | true | Proceed (recognized variable) | OK |
| `validator_exit_code == 0` | Stage 5 (FR-5) | Zero/Empty | n/a | n/a | n/a | OK |
| `validator_exit_code == 0` | Stage 5 (FR-5) | Typical | `0` | true | Proceed to Stage 6 | OK |
| `validator_exit_code == 0` | Stage 5 (FR-5) | Maximum/Overflow | `1`..`255` | false | Abort; marketplace repo unchanged (FR-9) | OK |
| `upstream clone succeeded` | Stage 1 (FR-2) | Zero/Empty | timeout/auth fail | false | Abort; exit ≠0 `UPSTREAM_CLONE_FAILED` | OK |
| `upstream clone succeeded` | Stage 1 (FR-2) | Typical | clone in <30s | true | Proceed | OK |
| `IronOps working tree clean` | Stage 0 (FR-12) | Sentinel | dirty | false | Abort; exit ≠0 `BUILDER_DIRTY_TREE` | OK |

No `GAP` entries — every guard has a specified behavior. Synthesis is not blocked.

---

## 10. Pipeline Flow Diagram [correctness focus — mandatory since this IS a pipeline]

```
[manifest.yaml: N=26 imports]
        |
        v
[Stage 1: Clone sources S=1]  --> [resolved_shas: S entries]
        |
        v
[Stage 2: Parse + validate manifest]  --> [N entries OR exit ≠0]
        |
        v
[Stage 3: Render to staging]
   N imports IN
       |
       +-- co-import check  --> rejected if missing companion --> exit ≠0
       +-- path-safety check --> rejected on escape           --> exit ≠0
       |
       v
   M files OUT (M may exceed N because directory imports fan out)
                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                Divergence point — Stage 4 must
                                annotate every emitted file in
                                META.json.sources[].imports[],
                                so N → M is observable.
        |
        v
[Stage 4: Write metadata]  --> +3 files (plugin.json, META.json, THIRD_PARTY_LICENSES.md)
                              +1 file at parent (marketplace.json)
        |
        v
[Stage 5: claude plugin validate]
        | exit 0 ?
        +---no---> ABORT; marketplace repo unchanged
        +---yes--> proceed
        |
        v
[Stage 6: rsync + git push]  --> +1 commit on marketplace repo
        |
        v
[Stage 7: Report]  --> stdout summary; non-blocking
```

**Divergence points (Stage 3 fanout: N=26 manifest entries → M=~150 files emitted):**

- The directory import `skills/sc-troubleshoot-protocol/` is ONE manifest entry but emits the full skill directory (SKILL.md + refs/ + rules/ + ...). META.json must enumerate every emitted file under that import so downstream consumers (audit, support) can reason at file granularity, not manifest-entry granularity.
- Downstream consumers of META.json should NOT assume `len(sources[*].imports) == len(manifest.imports)` — directory imports expand.

---

## 11. Hook Layout (Designed, Deferred from v0.1 Runtime)

The plugin spec slot for hooks is `hooks/hooks.json` at plugin root, with hook scripts under `scripts/` referenced via `${CLAUDE_PLUGIN_ROOT}`. When hooks are re-enabled (post-v0.1):

- A future manifest entry `kind: hook-config` imports `src/superclaude/hooks/hooks.json` to `hooks/hooks.json`.
- Hook scripts import as `kind: hook-script` to `scripts/<name>.sh`.
- The builder rewrites all `${CLAUDE_PLUGIN_ROOT}` references and enforces FR-8 path safety on hook scripts.
- Hook re-enablement requires a security review checkpoint documented in `release-notes-v0.2.md` (out of scope for this spec).

For v0.1, the manifest MUST NOT include any `kind: hook-config` or `kind: hook-script` entries. The builder treats those `kind` values as reserved.

---

## 12. Acceptance Criteria for v0.1 Release

**Definition of Done — must all be satisfied for the v0.1 release to ship:**

| # | Criterion | Verification |
|---|---|---|
| AC-1 | Builder runs to green on a clean Linux x86_64 CI runner with the committed `manifest.yaml`. | GitHub Actions log shows exit 0 |
| AC-2 | Rendered plugin tree contains all components in the v0.1 shortlist (§13). | Snapshot test against golden fixture |
| AC-3 | `claude plugin validate` passes on the staging plugin tree. | CI step exit 0 |
| AC-4 | `META.json` validates against the schema in §6 and lists every emitted file with a non-empty `resolved_sha`. | JSON schema + spot-check 3 file SHAs |
| AC-5 | `THIRD_PARTY_LICENSES.md` is present and references the upstream IronClaude license. | File existence + grep |
| AC-6 | Marketplace repo receives one new commit per build. Commit message contains `META.json.builder_version` and at least one source SHA. | `git log -1` on marketplace repo |
| AC-7 | From a fresh project: `claude plugin marketplace add IronbellyOrg/ironops-marketplace && claude plugin install ironops-devops@ironops && /reload-plugins`, then `/ironops-devops:troubleshoot` is callable. | Manual smoke test |
| AC-8 | All 16 FR-N have a corresponding CI test or assertion. | Test inventory mapping in `tests/test_inventory.md` |
| AC-9 | All Guard Boundary Table rows are exercised at least once across the CI test matrix. | Coverage report in build artifacts |
| AC-10 | Builder fails fast on every malformed-manifest fixture (empty, schema_version mismatch, self-overwrite, orphan command, path escape, dirty upstream). | Negative-test suite in CI |

---

## 13. v0.1 Component Shortlist (initial — finalized in task-builder phase)

Carried forward from decision brief §5. Lock the literal file list during the task-builder phase by verifying each upstream path exists at HEAD of `IronbellyOrg/IronClaude` at build time.

**Agents (11):** `devops-architect`, `system-architect`, `security-engineer`, `root-cause-analyst`, `performance-engineer`, `backend-architect`, `quality-engineer`, `pm-agent`, `self-review`, `technical-writer`, `requirements-analyst`.

**Skills (~8):** `sc-troubleshoot-protocol`, `sc-crash-recovery`, `sc-cli-portify-protocol`, `task`, `task-builder`, `tech-research`, `tdd`, `tech-reference`. (`prd` deferred — product artifact, not core infra.)

**Commands (~7):** `troubleshoot`, `git`, `cli-portify`, `cleanup-audit`, `task`, `research`, `workflow`. Each command's `Skill sc:<x>-protocol` invocation drives FR-4 co-imports.

**Total expected file count after directory expansion:** ~150 files (skills are directories).

---

## 14. Test Strategy [Crispin + Gregory closure]

| Test class | Target FRs | Implementation |
|---|---|---|
| Unit: manifest parser | FR-1, FR-14, FR-15, FR-16 | `pytest` cases on fixture YAML files |
| Unit: import resolver | FR-2, FR-3, FR-7 | mock upstream clones; assert resolved SHAs |
| Unit: co-import validator | FR-4 | fixture commands with and without skills |
| Unit: path-safety checker | FR-8 | string + filesystem fixtures |
| Integration: render-to-staging | FR-1..FR-8, FR-12 | end-to-end with a small two-file manifest |
| Integration: full v0.1 build | All | run the actual v0.1 manifest against a checked-out IronClaude fixture; snapshot output |
| Integration: validator gate | FR-5, FR-9 | inject a malformed plugin.json; assert no marketplace push |
| Integration: atomicity | FR-9 | kill builder mid-Stage-4; assert marketplace HEAD unchanged |
| Integration: golden output | AC-2 | snapshot diff against committed fixture |
| Negative: all malformed manifests | AC-10 | one fixture per `NFR-7` failure category |
| Smoke: install-and-invoke | AC-7 | nightly: install plugin in clean ephemeral project, run `/ironops-devops:troubleshoot` |

---

## 15. Risks and Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| IronClaude reorgs upstream paths | MAJOR | Manifest paths are the only coupling; reorg = manifest edit. FR-2 builder fails fast on missing paths. |
| `claude plugin validate` semantics change between Claude Code versions | MAJOR | Pin Claude Code version in CI; document in `CHANGELOG.md` on bumps. |
| Upstream license change | MAJOR | FR-11 emits attribution every build; release engineer audits licenses on each upstream SHA bump. |
| Disk-full on CI runner during clone of large upstream | MINOR | Shallow clone (`--depth=1`) by default; cleanup in `finally`. |
| Marketplace repo push race (two builds at once) | MINOR | GitHub Actions `concurrency: ironops-publish` group limits to one in-flight build. |
| Hooks re-enabled prematurely | MAJOR | FR §11 — `kind: hook-*` reserved; builder rejects until v0.2+ explicit unlock. |
| `${CLAUDE_PLUGIN_ROOT}` evolves (Claude Code rename) | MINOR | Single string constant in builder; one-line update on Claude Code change. |
| Skill content references `.claude/templates/...` paths at runtime | MAJOR | Discovery work in task-builder phase. If found, mitigation = builder rewrites or excludes that skill from v0.1 with documented gap. |

---

## 16. Open Questions (for task-builder / TDD-skipped, captured here)

1. **OQ-1 — Manifest schema YAML or TOML?** YAML recommended (matches IronClaude convention). Confirm during task-builder phase before locking schema.
2. **OQ-2 — Skill rename `sc-troubleshoot-protocol` → `troubleshoot-protocol`?** Cosmetic; user-visible skill name is set by `SKILL.md.name` frontmatter, not the directory. v0.1 keeps directory names unchanged to minimize blast radius.
3. **OQ-3 — Marketplace repo bootstrap.** Does `IronbellyOrg/ironops-marketplace` exist? If not, who creates it and with what initial commit? Assumes v0.1 builder will be allowed to push to an empty repo on first successful build.
4. **OQ-4 — Auth for upstream clones in CI.** Personal access token, GitHub App, or deploy key on the marketplace repo? Likely PAT in `GITHUB_TOKEN` secret for v0.1.
5. **OQ-5 — Test fixtures for upstream.** Snapshot a known-good IronClaude commit into `tests/fixtures/ironclaude/`, or fetch on demand in CI? Snapshot recommended for hermetic tests.
6. **OQ-6 — `prd` skill inclusion.** Included or excluded from v0.1? Spec lists as deferred; revisit during component-shortlist lock.
7. **OQ-7 — License audit cadence.** Per build, weekly, or per upstream SHA change? Per-build attribution is automatic (FR-11); a separate human license audit can be quarterly.
8. **OQ-8 — Builder output verbosity.** What's logged to stdout vs build-log-only? Affects CI dashboards.
9. **OQ-9 — `monitors/`, `.lsp.json`, `bin/`, `output-styles/`, `themes/`.** All confirmed out of scope; defer revisit to a future release planning doc.
10. **OQ-10 — Onboarding command** (`/ironops-devops:init` or similar). Not in v0.1; revisit in v0.2 once user feedback exists.

---

## 17. Definitions

- **Builder:** the Python package at `/config/workspace/IronOps/src/ironops/` (installable via `uv pip install -e .`, exposing the `ironops` CLI entry point per `pyproject.toml [project.scripts]`; `scripts/` is reserved for future helper scripts only — per gap-fill disposition **D4** in `research/05-gap-fill-disposition.md`) that consumes `manifest.yaml` and produces the rendered plugin tree.
- **Upstream:** any repository declared in `sources` (v0.1: just IronClaude).
- **Manifest:** the YAML file declaring sources and per-source imports.
- **Rendered plugin tree:** the on-disk staging directory containing `agents/`, `skills/`, `commands/`, `plugin.json`, `META.json`, `THIRD_PARTY_LICENSES.md`. Becomes `plugins/ironops-devops/` in the marketplace repo on publish.
- **Marketplace repo:** `IronbellyOrg/ironops-marketplace`, a private GitHub repo containing `.claude-plugin/marketplace.json` and `plugins/ironops-devops/`. The thing target projects add via `claude plugin marketplace add`.
- **Plugin cache:** `~/.claude/plugins/cache/` on the target developer's machine. Populated by `claude plugin install`. Read-only at runtime.
- **`${CLAUDE_PLUGIN_ROOT}`:** Claude-Code-resolved path to the plugin in the cache. Required for any in-plugin path reference per Claude Code spec.
- **`META.json`:** provenance manifest emitted by the builder (§6).

---

## 18. Next Step

Feed this spec into `/task-builder` to produce an MDTM task file. Paste-ready:

```
/task-builder Build a task file to implement v0.1 of the IronOps DevOps Claude Plugin (ironops-devops) per the spec at /config/workspace/IronOps/.dev/releases/1.0/0.1/SPEC_IRONOPS_DEVOPS_PLUGIN.md. Scope: greenfield IronOps repo at /config/workspace/IronOps/. Deliverables: manifest.yaml, Python builder (scripts/build_plugin.py + helpers), GitHub Actions workflow, test suite covering all 16 FRs, golden-output fixtures, malformed-manifest negative tests, and the initial v0.1 manifest covering the shortlist in spec §13. The spec is authoritative — every FR-N becomes a task item with the spec's acceptance criteria as the verification clause. Honor the open questions in §16 as decisions to make during build, not blockers.
```
