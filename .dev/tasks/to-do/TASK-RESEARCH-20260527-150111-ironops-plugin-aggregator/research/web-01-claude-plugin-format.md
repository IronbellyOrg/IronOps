# Web Research 01 — Claude Code Plugin Packaging Format

**Topic:** Current Claude Code plugin packaging format and capabilities
**Captured:** 2026-05-27 (Tavily extract)
**Sources:**
- <https://code.claude.com/docs/en/plugins>
- <https://code.claude.com/docs/en/plugins-reference>
**Status:** Complete

---

## 1. Plugin = a directory; manifest is optional

A Claude Code plugin is a directory. The manifest `.claude-plugin/plugin.json` is **optional** if components live in default locations. Source: plugins doc "Plugin structure overview".

### Default layout

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json          # Optional manifest
├── skills/
│   └── <name>/SKILL.md
├── commands/                # Flat .md skill files (legacy; docs recommend skills/ for new plugins)
├── agents/
│   └── <name>.md
├── hooks/
│   └── hooks.json
├── .mcp.json
├── .lsp.json
├── monitors/monitors.json
├── bin/                     # Added to Bash tool PATH while plugin is enabled
├── settings.json            # Only `agent` and `subagentStatusLine` keys currently supported
├── output-styles/
└── themes/                  # experimental
```

Source: plugins-reference doc "Plugin directory structure".

**Common mistake (called out explicitly in the docs):** Don't put `commands/`, `agents/`, `skills/`, or `hooks/` *inside* `.claude-plugin/`. Only `plugin.json` belongs in `.claude-plugin/`.

## 2. plugin.json schema (verbatim from `code.claude.com/docs/en/plugins-reference`)

```json
{
  "name": "plugin-name",
  "displayName": "Plugin Name",
  "version": "1.2.0",
  "description": "Brief plugin description",
  "author": { "name": "...", "email": "...", "url": "..." },
  "homepage": "https://...",
  "repository": "https://...",
  "license": "MIT",
  "keywords": ["keyword1", "keyword2"],
  "skills": "./custom/skills/",
  "commands": ["./custom/commands/special.md"],
  "agents": ["./custom/agents/reviewer.md"],
  "hooks": "./config/hooks.json",
  "mcpServers": "./mcp-config.json",
  "outputStyles": "./styles/",
  "lspServers": "./.lsp.json",
  "experimental": {
    "themes": "./themes/",
    "monitors": "./monitors.json"
  },
  "dependencies": [
    "helper-lib",
    { "name": "secrets-vault", "version": "~2.1.0" }
  ]
}
```

| Field | Required | Notes |
|---|---|---|
| `name` | yes | kebab-case, no spaces. Used as skill namespace: `/plugin-name:skill-name` |
| `version` | no | Explicit `version` pins the plugin — users only get updates when bumped. Omit and the git commit SHA is used (every commit = new version). |
| `description` | no | Shown in `/plugin` picker |
| `dependencies` | no | Plain string or `{name, version, marketplace}`. Semver ranges: `~2.1.0`, `^2.0`, `>=1.4`, `=2.1.0` |
| `skills` / `commands` / `agents` / `hooks` / `mcpServers` / `lspServers` / `outputStyles` | no | Each accepts string, array, or object — redirects from default paths |
| `userConfig` | no | Prompts user at enable time; supports `string`/`number`/`boolean`/`directory`/`file`, with `sensitive` for credentials |
| `channels` | no | Telegram/Slack/Discord-style message injection |
| `experimental.themes` / `experimental.monitors` | no | Experimental components |

## 3. Components that can live in a plugin

| Component | Default location | Purpose |
|---|---|---|
| Skills | `skills/<name>/SKILL.md` | Markdown skill packages, optionally with `refs/`, `rules/`, `templates/`, `scripts/` |
| Commands | `commands/<name>.md` | Flat-file skills; legacy form; docs recommend `skills/` for new plugins |
| Agents | `agents/<name>.md` | Subagent definitions. **Plugin subagents cannot use `hooks`, `mcpServers`, or `permissionMode` frontmatter — security policy.** |
| Hooks | `hooks/hooks.json` | Event handlers. Hook event vocabulary includes `SessionStart`, `Setup`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `SubagentStart/Stop`, `Stop`, `InstructionsLoaded`, `FileChanged`, `PreCompact/PostCompact`, plus ~15 others. Hook types: `command`, `http`, `mcp_tool`, `prompt`, `agent` |
| MCP servers | `.mcp.json` | Standard MCP config (`command`, `args`, `env`). Must use `${CLAUDE_PLUGIN_ROOT}` for any plugin-local paths |
| LSP servers | `.lsp.json` | Language Server Protocol configs |
| Monitors | `monitors/monitors.json` | Background processes (`tail -F` etc.); `when: "always"` or `"on-skill-invoke:<skill>"` |
| Executables | `bin/` | Added to Bash tool PATH while plugin enabled |
| Settings | `settings.json` | Only `agent` and `subagentStatusLine` keys currently supported |

## 4. Path / runtime contract

- Plugins are **copied** to `~/.claude/plugins/cache/` at install time, not symlinked. Paths like `../shared-utils` outside the plugin root **do not work**.
- Hooks and MCP server commands must reference plugin files via `${CLAUDE_PLUGIN_ROOT}` — relative paths break after caching.
- Persistent state goes to `${CLAUDE_PLUGIN_DATA}` (resolves to `~/.claude/plugins/data/{id}/`); survives plugin updates and uninstalls (unless `--keep-data` is omitted).
- `${CLAUDE_PROJECT_DIR}` available to MCP servers.

## 5. Local development & testing

```
claude --plugin-dir ./my-plugin            # Load a directory or .zip for the session
claude --plugin-dir ./one --plugin-dir ./two
claude --plugin-url https://example.com/my-plugin.zip
```

`/reload-plugins` picks up live edits without restart. Skills appear as `/<plugin-name>:<skill-name>`.

## 6. Validation

```
claude plugin validate ./my-plugin          # Checks plugin.json + skill/agent/command frontmatter + hooks.json
claude plugin validate ./my-marketplace     # When pointed at a marketplace, checks marketplace.json schema only
```

Validator catches: invalid JSON, missing required fields, malformed YAML frontmatter, malformed `hooks/hooks.json`, source path traversal in marketplace.

## 7. Version management

| Approach | Behavior | When to use |
|---|---|---|
| Explicit `version` in `plugin.json` | Users only update when you bump it | Published plugins with stable releases |
| Omit `version` | Commit SHA is used; every commit = update | **Internal/team plugins under active dev — explicitly recommended by docs** |

If `version` is set in both `plugin.json` and marketplace entry, `plugin.json` wins silently.

## 8. CLI surface

```
claude plugin install <plugin>@<marketplace> [--scope user|project|local]
claude plugin uninstall <plugin>             [--keep-data] [--prune]
claude plugin enable / disable / update / list / details / prune / tag
claude plugin validate <path> [--strict]
```

Plus interactive `/plugin` and `/plugin marketplace ...` commands inside Claude Code, and `/reload-plugins`.

## 9. Common pitfalls (from official docs)

| Issue | Cause | Fix |
|---|---|---|
| Plugin not loading | Invalid `plugin.json` | `claude plugin validate` |
| Skills not appearing | Wrong directory structure | `skills/` must be at plugin root, not inside `.claude-plugin/` |
| Hooks not firing | Script not executable | `chmod +x script.sh` |
| MCP server fails | Missing `${CLAUDE_PLUGIN_ROOT}` | Use the variable for all plugin paths |
| Path errors | Absolute paths used | All paths must be relative and start with `./` |
| Files-not-found post-install | Path references outside plugin dir | Plugins are cached; cannot reach `../shared-utils` |

## Key External Findings

- A Claude Code plugin can hold every component IronClaude wants to ship: agents, skills, commands, hooks, MCP servers, scripts, templates (carried as plain files inside skill packages or `bin/`), and project-level settings (limited).
- **Core framework files (`CLAUDE.md`, `PRINCIPLES.md`, `RULES.md`) have no first-class plugin slot.** They are project-level memory files. A plugin can ship them as skill `refs/` files or expose them via a skill that loads them, but a plugin cannot replace the project's `CLAUDE.md`.
- Skill naming is automatically namespaced per plugin, so collisions between plugins are not a real risk; collisions within a single plugin are caught by `claude plugin validate`.
- Hook safety: plugin-shipped subagents cannot define `hooks`, `mcpServers`, or `permissionMode`. Top-level plugin hooks DO load, but `allowManagedHooksOnly: true` in managed settings restricts them to admin-approved plugins.
- The recommended pattern for actively-developed internal plugins is **omit `version`** and let commit SHA drive updates.

## Recommendations from External Research

- Treat `${CLAUDE_PLUGIN_ROOT}` as a hard build-time invariant — all generated hook configs and MCP configs must use it.
- For v0.1 (internal-only, hooks deferred), the simplest path is: a plugin with `skills/`, `agents/`, optional `commands/`, optional `bin/`, no `hooks/hooks.json`, and no `.mcp.json`. The plugin design document should still describe the future hook layout.
- Plan to call `claude plugin validate` in CI for every build.
