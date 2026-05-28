# Research 01 — IronClaude Upstream Surface for IronOps

**Investigation type:** Code Tracer + Integration Mapper
**Scope:** `/config/workspace/IronClaude/src/superclaude/{agents,skills,commands,hooks,core,templates}` plus existing plugin build pipeline
**Status:** Complete
**Date:** 2026-05-27

---

## 1. Source-of-truth verification

| Claim | Evidence | Verdict |
|---|---|---|
| `src/superclaude/` is the canonical source of distributable components | `src/superclaude/core/CLAUDE.md:17-30`; `Makefile:109-163` (`sync-dev` reads only from `src/`); project `CLAUDE.md:139-159` | **[CODE-VERIFIED]** |
| `.claude/` is generated output of `src/` | `Makefile:165-353` (`verify-sync` enforces both-direction match); `.gitignore` excludes `.claude/` except `settings.json`; memory `feedback_claude_dir_gitignored.md` | **[CODE-VERIFIED]** |
| `plugins/superclaude/` is a frozen pre-reorg snapshot, not active source | `plugins/superclaude/` exists with `agents/`, `commands/`, etc., but `scripts/build_superclaude_plugin.py:18` references `plugins/superclaude/manifest/` that does not exist | **[CODE-CONTRADICTED — handoff doc treats it as active; reality is the manifest dir was never populated]** |
| Existing IronClaude `build-plugin` Makefile target works today | `Makefile:68-72` calls `python scripts/build_superclaude_plugin.py`; script requires `plugins/superclaude/manifest/metadata.json` which is missing | **[CODE-CONTRADICTED]** — the build target would fail on first invocation. **IronOps cannot depend on this script.** |

**Implication:** IronOps must implement its own builder. Reading from `src/superclaude/` (the true source of truth) is correct; the `plugins/superclaude/` directory is unreliable.

## 2. Component inventory (counts and shape)

Verified via `find /config/workspace/IronClaude/src/superclaude/{agents,skills,commands,hooks}`:

| Component dir | Count | Shape |
|---|---|---|
| `src/superclaude/agents/*.md` | 31 .md files (verified via Auggie research-notes from `TASK-RF-20260522-203947-tavily-agents-refactor`) | YAML frontmatter + Markdown body. Frontmatter includes `name`, `description`, `tools` |
| `src/superclaude/skills/<name>/SKILL.md` | Multiple skill directories. Each has `SKILL.md`; many have `refs/`, `rules/`, `templates/`, `scripts/` subdirs | Exactly matches Claude Code spec for `skills/<name>/SKILL.md` |
| `src/superclaude/commands/*.md` | 30+ command definitions | YAML frontmatter + Markdown body; many delegate to a same-named `sc:<name>-protocol` skill via `Skill` tool |
| `src/superclaude/hooks/hooks.json` | 1 unified file | Aggregates all event matchers across freshness, auggie, workspace-write, offer-pr-review |
| `src/superclaude/hooks/scripts/*.sh` | ~9 shell scripts | freshness-{session-start,user-prompt,pre-edit,post-read,subagent-start,subagent-stop,file-changed}.sh; reject-workspace-writes.sh; auggie-flag-clear.sh |
| `src/superclaude/core/*.md` | CLAUDE.md, RULES.md, PRINCIPLES.md (plus others) | Framework rule files; loaded into Claude Code as memory, not via plugin mechanism |
| `src/superclaude/templates/` | MDTM templates, roadmap templates | Used by the `task-builder` skill |

## 3. Suitability for an IronOps DevOps plugin

Candidate shortlist from the user's handoff doc, scored against IronOps DevOps focus:

### Agents — strong candidates

| Agent | DevOps fit | Inclusion |
|---|---|---|
| `devops-architect.md` | Core | **Include v0.1** |
| `system-architect.md` | Core | **Include v0.1** |
| `security-engineer.md` | Core (infra security) | **Include v0.1** |
| `root-cause-analyst.md` | Core (incident response) | **Include v0.1** |
| `performance-engineer.md` | Core (SRE) | **Include v0.1** |
| `backend-architect.md` | Adjacent (API/data) | **Include v0.1** |
| `quality-engineer.md` | Adjacent (CI quality gates) | **Include v0.1** |
| `pm-agent.md` | Workflow management | **Include v0.1** |
| `self-review.md` | Workflow management | **Include v0.1** |
| `technical-writer.md` | Runbook/postmortem authoring | **Include v0.1** |
| `requirements-analyst.md` | Spec clarification | **Include v0.1** |
| `frontend-architect.md` | Not infra | Skip |
| `business-panel-experts.md` | Not infra | Skip |
| `socratic-mentor.md`, `learning-guide.md` | Not infra | Skip |

### Skills — strong candidates

| Skill | DevOps fit | Inclusion |
|---|---|---|
| `sc-crash-recovery/` | Core (incident response) | **Include v0.1** |
| `sc-troubleshoot-protocol/` | Core | **Include v0.1** |
| `sc-cli-portify-protocol/` | Adjacent (CLI/script porting) | **Include v0.1** |
| `task-builder/`, `task/` | Workflow infrastructure | **Include v0.1** |
| `tech-research/` | Investigation | **Include v0.1** |
| `prd/`, `tdd/`, `tech-reference/` | Spec/design | **Include v0.1** (useful for infra design work) |

### Commands — strong candidates (verify each via Read in PRD phase)

`troubleshoot.md`, `git.md`, `cli-portify.md`, `cleanup-audit.md`, `task.md`, `research.md`, `test.md`, `implement.md`, `workflow.md`, `spawn.md`, `recommend.md`.

### Hooks — deferred from v0.1 runtime per user direction

Design only. Files to study: `hooks.json`, `freshness-*.sh`, `reject-workspace-writes.sh`, `auggie-flag-clear.sh`.

### Core framework files — not first-class plugin components

Claude Code plugins have no slot for project `CLAUDE.md`. Two options:

- Ship `CLAUDE.md`, `RULES.md`, `PRINCIPLES.md` as `skills/<name>/refs/` files referenced by skills that need them.
- Ship a `bin/ironops-init` (or similar) command that scaffolds `.claude/CLAUDE.md` into target projects (out of scope for v0.1).

### Python helpers (`pm_agent/`, `execution/`)

These are pytest-side runtime helpers, not Claude Code components. They have no slot in a plugin and should not be included. Skip.

## 4. Integration constraints surfaced

1. **Sync-dev rewrites paths.** IronClaude's `Makefile:109-163` copies `src/superclaude/commands/*.md` to `.claude/commands/sc/*.md`. The `sc/` directory mapping is part of how skills get a `/sc:<name>` slash command in IronClaude. **For IronOps, the per-plugin namespace replaces this** — a skill at `ironops-devops/skills/troubleshoot/SKILL.md` becomes `/ironops-devops:troubleshoot`. No name rewriting is needed in IronOps.
2. **Command-to-skill coupling.** Many IronClaude commands invoke a same-named protocol skill (e.g., `troubleshoot.md` → `Skill sc:troubleshoot-protocol`). If IronOps copies a command without its skill it breaks. Manifest must enforce co-import.
3. **Skill `refs/` paths.** Skills load companion files from `refs/`, `rules/`, `templates/`. Builder must copy the full skill directory, not just `SKILL.md`.
4. **Hook scripts cite each other and the agent files.** `auggie-flag-clear.sh` references the agent + tool matcher regex in `hooks.json`. If hooks land in a future release, they import as a bundle, not piecemeal.
5. **Licensing.** IronClaude is under SuperClaude licensing (likely MIT per `LICENSE` file). IronOps must preserve attribution; recommended to ship a `THIRD_PARTY_LICENSES.md` enumerating each imported file's upstream license.

## 5. Build pipeline gaps in IronClaude (not IronOps' problem to fix)

- `scripts/build_superclaude_plugin.py` is unrunnable (missing manifest dir).
- `plugin.json` stub at `.claude-plugin/plugin.json` is half-populated.
- No CI runs the existing plugin build.

These are problems for the IronClaude maintainers. The IronOps builder should pull from `src/superclaude/` (the source of truth) and ignore both `plugins/superclaude/` and `scripts/build_superclaude_plugin.py`.

## Gaps and Questions

- Need explicit licensing confirmation for `src/superclaude/agents/business-panel-experts.md` and others ported from upstream upstreams (deferred to PRD).
- Need to confirm the precise list of skills that the v0.1 shortlist depends on transitively (e.g., does `task-builder` reference templates IronOps must also copy?). Resolved in PRD scope work.
- Need to confirm any skills that load `.claude/templates/` directly at runtime (those would break under plugin-cache paths). Resolved in TDD work.

## Summary

IronClaude has more than enough DevOps-relevant agents, skills, and commands to back a meaningful v0.1 plugin (~11 agents, 5-8 skills, 8-10 commands). The source of truth is unambiguously `src/superclaude/`; the existing `plugins/superclaude/` and `scripts/build_superclaude_plugin.py` are partially-built dead ends and should be ignored. The main integration risks are co-import (commands → skills → refs/templates) and licensing/attribution, both manageable via the manifest design.
