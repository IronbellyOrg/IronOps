# Decision Brief: IronOps DevOps Claude Plugin — Aggregator Strategy

**Date:** 2026-05-27
**Author:** sc-recommend / tech-research (Claude Code session)
**Audience:** RyanW (IronOps owner)
**Decision needed:** Which of four aggregation strategies to adopt for the IronOps DevOps Claude Code plugin (v0.1).
**Evidence trail:** `research/research-notes.md`, `research/web-01-claude-plugin-format.md`, `research/web-02-marketplace-distribution.md`, `research/01-ironclaude-upstream-surface.md` (all in this task folder).

---

## 1. Problem in one paragraph

We want infrastructure / CI-CD / SRE projects to install a **single Claude Code plugin** that bundles a curated set of DevOps-relevant agents, skills, and commands from IronClaude (today) plus future custom IronOps assets and other upstream repos (later). IronClaude files must remain read-only; their latest mainline must be pulled at build time, not forked or patched; and target projects must not vendor `.claude/` mirrors. Hooks are designed but deferred from v0.1 runtime. Distribution is internal-only.

## 2. Options compared

| Aspect | A — Direct upstream plugin deps | **B — One curated aggregator plugin (recommended)** | C — Multiple focused plugins | D — File-copy installer |
|---|---|---|---|---|
| Target installs | N upstream plugins | **1 plugin (`/plugin install ironops-devops@ironops`)** | N IronOps plugins (or 1 + auto-deps) | 1 CLI invocation per project |
| Curation surface | None — all upstream commands/skills exposed | **Manifest allowlist; only selected items shipped** | Per-plugin manifest | Manifest allowlist |
| Always-latest upstream | Built-in via Claude Code auto-update | **Build CI pulls latest mainline on each release** | Same as B | Manual re-run of installer |
| No vendoring `.claude/` into target | ✅ | ✅ | ✅ | ❌ writes into target's `.claude/` |
| Provenance / source SHAs | ❌ | **✅ builder writes META.json with per-file source repo + SHA** | ✅ | ✅ at install time only |
| Hooks deferable | ⚠️ all-or-nothing inheritance | **✅ manifest simply omits hook files in v0.1** | ✅ | ⚠️ same as A |
| Native update/disable/uninstall | ✅ | ✅ | ✅ | ❌ users delete files manually |
| Skill name collisions | Multiple `/x:y` prefixes; UX clutter | **Single namespace `/ironops-devops:*`** | Several namespaces (acceptable) | None (no plugin layer); but `.claude/` collisions become possible |
| **Blocked today?** | **Yes — IronClaude's own plugin pipeline is half-built (manifest dir missing, `build_superclaude_plugin.py` would fail).** Nothing to depend on. | No | No | No |
| Future split flexibility | n/a | **Easy — split when justified; deps field supports `{name, version: "~x.y"}` constraints** | Already split | Easy to add more file groups |

### Why Option A is currently impossible

`scripts/build_superclaude_plugin.py:18` references `plugins/superclaude/manifest/`, which does not exist in the current IronClaude checkout. IronClaude has no actively-built published plugin to depend on, and fixing that pipeline is IronClaude's roadmap — not ours. Even if it were running, Option A would expose every command upstream ships, which violates the curation constraint.

### Why Option D is unappealing

Writing into each target repo's `.claude/` directly defeats the source-of-truth discipline IronClaude itself enforces (`make verify-sync`, the project's "never commit `.claude/`" rule), creates per-repo drift, and forfeits Claude Code's first-class update/disable/uninstall flow.

### Why Option C is overkill at v0.1

Splitting along DevOps / SRE / Security / Workflow boundaries is plausible at v0.5+ but adds dependency-management overhead (semver tags, `{plugin-name}--v{version}` git tags, cross-marketplace allow-lists) before we know whether users want that surface area. The plugin spec supports it — we can grow into it.

## 3. Why Option B fits the constraints best

1. **Claude Code natively supports the curated-aggregator pattern.** Either (a) the marketplace entry uses `strict: false` and the marketplace catalog declares the components for a raw upstream plugin, OR (b) our builder renders a fully-formed plugin with its own `plugin.json` and we ship that. Option (b) is simpler when we curate from multiple upstreams, which is the user's stated direction.
2. **A private GitHub repo containing both `.claude-plugin/marketplace.json` and the rendered plugin satisfies "internal-only".** Auth via `GITHUB_TOKEN` for headless auto-update. Optional `CLAUDE_CODE_PLUGIN_SEED_DIR` for airgapped CI runners.
3. **Always-latest mainline is a CI/build-time concern, not a runtime concern.** The builder clones `IronbellyOrg/IronClaude@HEAD`, reads our manifest allowlist, copies files into the curated plugin, records source SHAs in a `META.json` shipped inside the plugin. Bumping a commit on the marketplace repo is the user-visible release; omitting `plugin.json.version` means every commit auto-updates installed plugins (the docs' explicitly-recommended pattern for internal/team plugins).
4. **Hooks defer cleanly.** v0.1 manifest simply doesn't list hook files. The TDD documents the future layout (`hooks/hooks.json` at plugin root, scripts under `bin/` or `scripts/`, `${CLAUDE_PLUGIN_ROOT}` references) so we don't lose the design.
5. **One namespace, low UX cost.** `/ironops-devops:troubleshoot`, `/ironops-devops:task`, etc. No collision with the user's other plugins; no `sc:` rewriting required.

## 4. Recommended product direction

**Adopt Option B: one curated build-time aggregator plugin.**

| Decision | v0.1 value |
|---|---|
| Plugin name | `ironops-devops` (slash-form: `/ironops-devops:<skill>`) |
| Marketplace name | `ironops` (kebab-case; not on the Anthropic reserved-name list) |
| Distribution shape | Private GitHub repo `IronbellyOrg/ironops-marketplace` containing `.claude-plugin/marketplace.json` + a `plugins/ironops-devops/` subtree rendered by the builder |
| Builder lives in | `/config/workspace/IronOps/` — `manifest.yaml` + `scripts/{fetch_sources.py,build_plugin.py,verify_plugin.py}` + GitHub Actions workflow. **Builder is implementation-language flexible — Python recommended for parity with IronClaude tooling.** |
| Upstream consumption | Build-time `git clone IronbellyOrg/IronClaude && checkout HEAD` (latest mainline). No local fork, no patches. Sources record commit SHA in `META.json`. |
| Version strategy v0.1 | **Omit `plugin.json.version`.** Commit SHA on `ironops-marketplace` drives updates. Switch to explicit semver when we have a release cadence (~v0.5). |
| Hooks | **Designed in TDD, omitted from v0.1 runtime.** Manifest does not list hook files; the plugin ships no `hooks/hooks.json`. Re-enable in a later release once we've decided on the safety model. |
| MCP servers | **Excluded from v0.1.** IronClaude's MCP configs are user/system-level (Auggie, Tavily, etc.) — not appropriate to bundle in a plugin. Re-evaluate per-server in a later release. |
| Core framework files (`CLAUDE.md`, `RULES.md`, `PRINCIPLES.md`) | **Not bundled as plugin components** — they have no plugin slot. Optionally ship them as `refs/` inside skills that need them; otherwise leave them as project-level concerns. |
| Validation gate | `claude plugin validate` in CI on every build; fail the release if it errors. |
| Provenance | `ironops-devops/META.json` with `{built_at, builder_version, sources: [{repo, ref, sha, manifest_paths: [...]}]}`. |

## 5. v0.1 scope (concrete shortlist)

From `research/01-ironclaude-upstream-surface.md`, curated for DevOps focus:

- **Agents (11):** `devops-architect`, `system-architect`, `security-engineer`, `root-cause-analyst`, `performance-engineer`, `backend-architect`, `quality-engineer`, `pm-agent`, `self-review`, `technical-writer`, `requirements-analyst`.
- **Skills (~8):** `sc-troubleshoot-protocol`, `sc-crash-recovery`, `sc-cli-portify-protocol`, `task`, `task-builder`, `tech-research`, `tdd`, `tech-reference` (and `prd` is optional — it's a product artifact but useful for infra design work).
- **Commands (~7):** confirm via Read in PRD phase — first pass: `troubleshoot`, `git`, `cli-portify`, `cleanup-audit`, `task`, `research`, `workflow`. Each command imports its companion skill (the manifest must enforce co-import — many commands delegate via `Skill sc:<name>-protocol`).
- **Hooks:** none in v0.1 runtime. Design recorded in TDD.

Final scope is locked in the PRD, not here.

## 6. Risks and how Option B handles them

| Risk | Option B mitigation |
|---|---|
| IronClaude reorgs its tree | Manifest paths are the only coupling; reorg = manifest edit, not a plugin re-architecture |
| Command-without-skill breakage | Builder validates co-imports against the manifest; CI fails the build if a command's `Skill sc:<x>-protocol` invocation references an unimported skill |
| Files-outside-plugin-root references at runtime | Builder rewrites any `${CLAUDE_PLUGIN_ROOT}`-relative references; rejects anything that escapes the plugin root |
| Licensing | `THIRD_PARTY_LICENSES.md` shipped inside the plugin, enumerating each imported file's upstream license |
| Stale upstream pulled at build time | Builder records exact commit SHA per file. Rollback = re-render at an earlier SHA |
| Hook safety unknown for plugin distribution | v0.1 ships zero hooks. TDD captures the design; ship in a later release once vetted |
| Future need to split into focused plugins | `plugin.json.dependencies` is built for this. We can split without disrupting target projects (they keep installing one plugin; it just gains auto-installed deps) |

## 7. What this does *not* decide

These are PRD/TDD scope, not decisions for this brief:

- The literal manifest YAML schema and per-file import directives.
- Final v0.1 component list (decided in PRD).
- Builder language (Python recommended but not blocking).
- Hook safety model and re-enablement criteria for v0.2+.
- Whether to also publish to the public community marketplace in the future.

## 8. Recommendation, restated

Adopt **Option B — one curated build-time aggregator plugin (`ironops-devops`), distributed via a private GitHub marketplace repo, omit-version mode, hooks deferred, MCP excluded for v0.1.**

## 9. Suggested next step (paste-ready)

If you approve Option B, run:

```
/prd Create a Feature-scope PRD for the IronOps DevOps Claude Code Plugin (v0.1). Use the decision brief at /config/workspace/IronOps/.dev/tasks/to-do/TASK-RESEARCH-20260527-150111-ironops-plugin-aggregator/DECISION-BRIEF-ironops-aggregator.md as the foundation. Output the PRD to /config/workspace/IronOps/docs/PRD_IRONOPS_DEVOPS_PLUGIN.md. Focus areas: the curated aggregator pattern, manifest schema requirements, build/publish flow, validation, provenance, hook deferral, distribution shape (private GitHub marketplace), v0.1 component shortlist. The PRD must call out scope boundaries (no MCP, no hooks, no core CLAUDE.md replacement) explicitly.
```

After PRD approval, follow with `/tdd` against the PRD.
