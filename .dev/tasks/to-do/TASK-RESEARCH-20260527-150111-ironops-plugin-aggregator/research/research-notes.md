# Research Notes: IronOps DevOps Claude Plugin — Aggregator Feasibility

**Date:** 2026-05-27
**Scenario:** A (explicit request — goals, constraints, source repo, and output type all provided)
**Depth Tier:** Standard (decision-brief scope; not a full implementation plan yet)
**Status:** Complete

---

## EXISTING_FILES

### Target workspace

- `/config/workspace/IronOps/` — bare repo: `LICENSE`, `README.md`, `.dev/releases/1.0/0.1/` only. No `pyproject.toml`, no `Makefile`, no `src/`, no `.claude/`, no build tooling. This is a greenfield aggregator project.

### Upstream (IronClaude) — read-only inputs

Verified directly via `Read`/`Bash` against `/config/workspace/IronClaude/`:

| Path | Role | Evidence |
|------|------|----------|
| `src/superclaude/` | **Canonical** source of truth for skills/agents/commands/hooks/core | `src/superclaude/core/CLAUDE.md:17-30`, project CLAUDE.md line 141 |
| `src/superclaude/agents/*.md` | 31 agent definitions (devops-architect, system-architect, security-engineer, root-cause-analyst, performance-engineer, backend-architect, quality-engineer, pm-agent, self-review, technical-writer, requirements-analyst, plus skip-candidates) | Confirmed by handoff doc and Auggie |
| `src/superclaude/skills/*` | Skills as directories with `SKILL.md` | confirmed by Makefile:115 `if [ -f "$$skill_dir/SKILL.md" ]` |
| `src/superclaude/commands/*.md` | Slash command definitions; sync target is `.claude/commands/sc/` (Makefile:131) | Makefile:131-136 |
| `src/superclaude/hooks/hooks.json` | Single hook config aggregating all event matchers | confirmed via `find` |
| `src/superclaude/hooks/scripts/*.sh` | freshness-*, reject-workspace-writes, auggie-flag-clear | confirmed via `find`; copied flat into `.claude/hooks/` (Makefile:137-143) |
| `src/superclaude/scripts/session-init.sh` | Optional session-init hook source | Makefile:144-147 |
| `src/superclaude/templates/` | MDTM templates + roadmap templates (skill input) | Makefile:148-157 |
| `src/superclaude/core/{CLAUDE.md,PRINCIPLES.md,RULES.md}` | Framework rule files | confirmed via Read |
| `src/superclaude/pm_agent/{confidence.py,self_check.py,reflexion.py}` | Python runtime helpers consumed by pytest fixtures, **not by Claude Code** | project CLAUDE.md "PM Agent" section |
| `src/superclaude/execution/parallel.py` | Python runtime — pytest-side parallel execution helper | project CLAUDE.md "Parallel Execution" |

### IronClaude's existing plugin packaging machinery (study reference, NOT inheritable as-is)

| Path | Status | Notes |
|------|--------|-------|
| `scripts/build_superclaude_plugin.py` | Present; references `plugins/superclaude/manifest/` that **does not exist** in current checkout. Would fail with `Missing plugin sources` on the manifest read. **[CODE-CONTRADICTED — handoff doc references a working pipeline; reality is the manifest dir was never populated]** | Confirmed via `Bash ls plugins/superclaude/manifest` → "No such file or directory" |
| `scripts/sync_from_framework.py` | Present; rewrites command/agent names with `sc:`/`sc-` namespace prefixes — **inverse** of what IronOps needs (IronOps is the consumer, not the source) | Read lines 1-220 |
| `Makefile` `build-plugin` / `sync-plugin-repo` targets | Present (Makefile:68-87) but depend on the broken `build_superclaude_plugin.py` | Read |
| `plugins/superclaude/` | Pre-reorg snapshot — has `agents/`, `commands/`, `core/`, `hooks/`, `mcp/`, `modes/`, `scripts/`, `skills/`, `templates/`, but NO `manifest/` and NO tests | confirmed via `find` |
| `.claude-plugin/plugin.json` | Stub with `name: "sc"`, `version: "4.3.0"`, empty repository/homepage | Read |
| `docs/research/dev-guide-research/extract-{opus,haiku}-03-plugin-reorg.md` | Design intent for a sync-from-framework → curated-plugin pipeline (one repo, not multi-source). **Predates the v0.1 Claude Code plugin spec — its tree (`.claude-plugin/plugin.json`, `skills/`, `commands/`, `agents/`, `hooks/`) matches the current spec** | Read |
| `docs/planning/devops-claude-plugin-handoff.md` | Source of the user's prompt — contains the same 15 design questions and component shortlist | confirmed via Auggie hit |

### Authoritative external evidence (code.claude.com/docs, fetched 2026-05-27)

| URL | Captured at | Key facts extracted |
|-----|-------------|---------------------|
| `code.claude.com/docs/en/plugins` | `.../research/web-01-claude-plugin-format.md` | Plugin layout: `.claude-plugin/plugin.json` (optional if defaults used), `skills/`, `commands/`, `agents/`, `hooks/`, `.mcp.json`, `.lsp.json`, `monitors/`, `bin/`, `settings.json` |
| `code.claude.com/docs/en/plugins-reference` | `.../research/web-01-claude-plugin-format.md` | Full schema: `name` required; optional `version`, `dependencies` (with semver), `userConfig`, `experimental.{themes,monitors}`. `commands`/`agents`/`skills` etc. can be re-pointed via plugin.json paths |
| `code.claude.com/docs/en/plugin-marketplaces` | `.../research/web-02-marketplace-distribution.md` | Marketplace = `.claude-plugin/marketplace.json`. Sources: relative path, `github`, `url`, `git-subdir`, `npm`. `strict: false` lets the marketplace own component definitions instead of `plugin.json` |
| `code.claude.com/docs/en/plugin-dependencies` | `.../research/web-02-marketplace-distribution.md` | `dependencies` field with semver ranges; cross-marketplace requires `allowCrossMarketplaceDependenciesOn`; failure modes: `dependency-unsatisfied`, `range-conflict`, `dependency-version-unsatisfied`, `no-matching-tag` |
| `code.claude.com/docs/en/discover-plugins` | `.../research/web-02-marketplace-distribution.md` | Install via `/plugin install name@marketplace`, scopes `user`/`project`/`local`/`managed`, `extraKnownMarketplaces` for project pinning, `CLAUDE_CODE_PLUGIN_SEED_DIR` for offline/airgap, version resolution: explicit `version` field OR commit SHA |

---

## PATTERNS_AND_CONVENTIONS

### Claude Code plugin spec (verified from official docs)

- A plugin is a directory; `.claude-plugin/plugin.json` is **optional** if components live in default locations.
- Components Claude Code recognizes inside a plugin:
  - `skills/<name>/SKILL.md`
  - `commands/<name>.md` (flat md files; docs recommend `skills/` for new work)
  - `agents/<name>.md`
  - `hooks/hooks.json`
  - `.mcp.json`, `.lsp.json`, `monitors/monitors.json`, `bin/`, `settings.json`, `output-styles/`, experimental `themes/`
- `plugin.json` schema includes: `name` (required, kebab-case), `version`, `description`, `author`, `homepage`, `repository`, `license`, `keywords`, `skills`/`commands`/`agents`/`hooks`/`mcpServers`/`outputStyles`/`lspServers` (each accepts string|array to redirect from defaults), `experimental.{themes,monitors}`, `dependencies`, `userConfig`, `channels`.
- **Skill namespacing**: a plugin named `ironops-devops` exposes its skill `troubleshoot` as `/ironops-devops:troubleshoot` (slash + plugin-name + colon + skill-name). Two plugins cannot collide on the same name (verified: "multiple plugins can coexist without name collisions" via per-plugin namespace).
- **Path discipline inside a plugin**: hooks and MCP server commands must use `${CLAUDE_PLUGIN_ROOT}` (not relative `./`) because the plugin is copied to `~/.claude/plugins/cache/` at install time. Persistent state must use `${CLAUDE_PLUGIN_DATA}`. Path traversal (`../shared-utils`) outside the plugin root **does not work** post-cache.
- **Hooks safety**: plugin subagents do NOT support `hooks`, `mcpServers`, or `permissionMode` frontmatter (security policy). Hooks live only in `hooks/hooks.json` at plugin root.
- **Version resolution**: explicit `version` in `plugin.json` wins; otherwise marketplace `version`; otherwise commit SHA (every commit = new version). Omitting `version` is the recommended pattern for internal/team plugins under active development.
- **Updates**: `/plugin update`, `/plugin marketplace update`, and `CLAUDE_CODE_PLUGIN_SEED_DIR` for pre-seeded container images.
- **Dependencies**: declared in `plugin.json.dependencies`, resolved against `{plugin-name}--v{version}` git tags created by `claude plugin tag --push`. Cross-marketplace dependencies require explicit allow-listing on the root marketplace.

### Marketplace mechanics

- A marketplace is `.claude-plugin/marketplace.json` at a repo root listing plugins and where to fetch each one.
- Plugin sources: relative path (same repo), `github`, `url` (git URL), `git-subdir` (subdirectory of a monorepo, sparse clone), `npm`.
- `strict: false` on a marketplace entry lets the marketplace catalog declare components for a plugin that does NOT have its own `plugin.json` — useful when curating someone else's raw files differently than they intended.
- For **private** marketplaces: HTTPS via `gh auth login`/credential helper; auto-update at startup needs `GITHUB_TOKEN`/`GL_TOKEN`/`BITBUCKET_TOKEN` in env.
- For **airgap/CI**: pre-seed via `CLAUDE_CODE_PLUGIN_SEED_DIR=/path/to/seed`. Read-only at runtime; auto-updates disabled for seeded marketplaces.

### IronClaude source-of-truth discipline (mandatory for IronOps to honor)

- Project CLAUDE.md lines 18-43 + memory `feedback_claude_dir_gitignored.md`: `.claude/{skills,commands,agents,hooks,templates}/*` is generated output of `src/superclaude/`. Anything IronOps consumes MUST be taken from `src/superclaude/`, never from `.claude/`. **IronClaude itself enforces this in CI via `make verify-sync`.**

### IronClaude's existing aggregator pattern is **single-source**

The existing `scripts/build_superclaude_plugin.py` + `plugins/superclaude/` layout assumes one upstream (itself). It rewrites command/agent names with `sc:`/`sc-` prefixes (`scripts/sync_from_framework.py:96-147`). IronOps needs **multi-source** aggregation and **no name rewriting** (we want `/ironops-devops:troubleshoot`, not `/sc:troubleshoot` — the plugin name does the namespacing for us).

---

## SOLUTION_RESEARCH

### Option space (the four the user asked us to compare)

**A. Direct upstream plugin dependencies.** Target projects install IronClaude's own published plugin(s) directly via `/plugin install ...@claude-plugins-official` (or a private mirror), plus any other upstream plugins. No aggregator.

**B. One curated aggregator plugin (the user's preferred direction).** IronOps builds and publishes a single `ironops-devops` plugin to a private marketplace. Build-time CI clones IronClaude (and future upstreams), reads a manifest allowlist, copies selected files into a curated `ironops-devops/` plugin tree, renders `plugin.json` and `marketplace.json`, and pushes to the distribution channel.

**C. Multiple focused plugins.** Several IronOps plugins (e.g., `ironops-troubleshoot`, `ironops-task`, `ironops-security`), each curated separately. Marketplace lists them all.

**D. Simple file-copy installer.** A CLI/script that target projects run (`ironops install` or similar) that copies curated files into `.claude/skills/` etc. directly. No plugin system involvement.

### Evaluation against user's stated constraints

| Constraint | A: direct deps | B: one aggregator | C: multi-plugin | D: file-copy |
|---|---|---|---|---|
| **Install one thing only** | ❌ user installs N upstream plugins | ✅ single `/plugin install ironops-devops@ironops` | ❌ N installs (mitigated if deps used: install one with N deps) | ✅ one CLI invocation |
| **No upstream exposure of every command** | ❌ user sees everything IronClaude ships | ✅ allowlist curates | ✅ per-plugin curation | ✅ allowlist curates |
| **Always-latest upstream** | ✅ Claude Code auto-update from upstream marketplace | ✅ build CI pulls latest mainline each release | ✅ same as B | ⚠️ user must re-run installer; no Claude-Code-native update path |
| **No local forks / no modified IronClaude copies** | ✅ direct consumption | ✅ if builder never edits content | ✅ same as B | ✅ if installer never edits content |
| **No vendoring `.claude/` into target repos** | ✅ plugin cache lives in `~/.claude/plugins/cache/` | ✅ same | ✅ same | ❌ writes into target repo's `.claude/` |
| **Hooks design now, defer runtime to >v0.1** | ⚠️ inherits upstream hooks immediately; cannot defer per-file | ✅ builder simply omits hook scripts from manifest for v0.1; spec describes them | ✅ same as B | ⚠️ same as A — file-copy hooks land immediately if copied |
| **Provenance / source SHAs recorded** | ❌ no central record | ✅ builder records source repo + commit SHA per file in `plugin.json` or sidecar | ✅ same as B | ✅ installer logs but doesn't survive runtime |
| **Dependency / collision safety** | ⚠️ same-name skills across upstream plugins are namespaced per plugin but UX has many `/x:y` prefixes | ✅ single namespace (`/ironops-devops:foo`) | ⚠️ same as A; mitigated by dependencies field | ✅ no plugin layer involved, but files in `.claude/` are unnamespaced — collisions with project-local skills become possible |
| **CI / build-time aggregation feasible** | n/a (no aggregation) | ✅ matches build-time-aggregator pattern user asked for | ✅ same | ✅ but the "aggregation" target is each user's machine, not CI |
| **Built-in Claude Code update/uninstall/disable** | ✅ `/plugin update`, `/plugin disable` | ✅ same | ✅ same | ❌ users must manually delete files |

### Discovery findings that change the analysis

1. **Claude Code already supports curated aggregation via `strict: false` marketplace entries.** A marketplace entry with `strict: false` can list components from a raw plugin repo and the marketplace operator decides what is exposed. That mechanism is built for the curated-aggregator pattern Option B describes. ([web-02])
2. **`git-subdir` plugin source allows pulling specific subdirectories of an upstream monorepo at install time via sparse clone.** This means Option A could in principle let IronOps publish a marketplace that points at `IronClaude/plugins/superclaude/skills/sc-troubleshoot-protocol/` directly without copying. ([web-02])
3. **IronClaude's existing plugin pipeline is incomplete** (`plugins/superclaude/manifest/` directory missing → `build_superclaude_plugin.py` would fail). So we cannot "just consume the upstream plugin" today — there is no published upstream plugin to depend on. This blocks Option A in its pure form.
4. **IronClaude is also still actively reshaping its plugin layout** (per `docs/research/dev-guide-research/extract-*-03-plugin-reorg.md`). Pinning IronOps to a specific IronClaude subdirectory layout would be fragile against upstream reorg. Manifest-driven copy isolates IronOps from layout churn.

---

## RECOMMENDED_OUTPUTS

| Output | Path | Status |
|---|---|---|
| Research notes (this file) | `.../research/research-notes.md` | Complete |
| Web research 01 — Claude Code plugin packaging spec | `.../research/web-01-claude-plugin-format.md` | Created this turn |
| Web research 02 — Marketplace, distribution, dependencies | `.../research/web-02-marketplace-distribution.md` | Created this turn |
| Codebase research 01 — IronClaude upstream surface for IronOps | `.../research/01-ironclaude-upstream-surface.md` | Created this turn |
| **Decision brief** (user's first deliverable) | `.../DECISION-BRIEF-ironops-aggregator.md` | Created this turn |
| Future: RESEARCH-REPORT (full skill output) | `.../RESEARCH-REPORT-ironops-aggregator.md` | Deferred — not needed for decision brief |
| Future: PRD | `docs/PRD_IRONOPS_DEVOPS_PLUGIN.md` (in IronOps) | Next phase after brief approval |
| Future: TDD | `docs/TDD_IRONOPS_BUILDER.md` (in IronOps) | After PRD approval |

---

## SUGGESTED_PHASES

Skipped for this run — the user's first ask is a decision brief, not a full tech-research pipeline. Files persist in the task workspace so a full run can resume here later if the user wants the formal RESEARCH-REPORT.

If we later want the formal pipeline:

- Phase 2 codebase agents: (1) IronClaude commands/skills/agents inventory + suitability scoring for DevOps; (2) Existing IronClaude build pipeline gaps; (3) MCP and hooks surface; (4) Source-of-truth and licensing.
- Phase 4 web agents: (1) Plugin packaging spec (done); (2) Marketplace/dependency mechanics (done); (3) Private/airgap distribution patterns; (4) Plugin security and hook safety.
- Phase 5 synthesis: standard 6-file mapping.

---

## TEMPLATE_NOTES

Not applicable for this run — the user's deliverable is a decision brief, not an MDTM-tracked task file. If we run the full pipeline later, **Template 02** (Complex Task) is the right choice (multi-phase, parallel agents, QA gates).

---

## AMBIGUITIES_FOR_USER

None blocking the decision brief. Open items to confirm before PRD:

1. **Distribution channel for "internal-only".** Three viable shapes:
   - Private GitHub repo + `claude plugin marketplace add ironbelly-org/ironops-marketplace`
   - Self-hosted git URL
   - `CLAUDE_CODE_PLUGIN_SEED_DIR` baked into CI container images
   Decision can wait until TDD.
2. **Plugin name confirmed:** `ironops-devops` (user said "IronOps DevOps Claude Plugin is fine"). Skill namespacing pattern becomes `/ironops-devops:<skill>`. Worth confirming the literal kebab-case before PRD.
3. **Where the builder lives long-term.** Two options: (a) a new repo `IronbellyOrg/ironops-builder` separate from IronOps marketplace, (b) builder + manifest + generated plugin all in `/config/workspace/IronOps/`. Decide in PRD/TDD.
4. **Hook v0.1 deferral mechanism.** Two ways: (a) builder simply omits hook files from the manifest allowlist for v0.1; (b) builder copies hook files but disables them via a generated `hooks/hooks.json` that excludes them. Option (a) is simpler and is what the brief recommends.
