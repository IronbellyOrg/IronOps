# Web Research 02 — Marketplace, Distribution, Dependencies, Updates

**Topic:** How Claude Code plugin marketplaces, dependencies, updates, and airgap deployment work
**Captured:** 2026-05-27 (Tavily extract)
**Sources:**
- <https://code.claude.com/docs/en/plugin-marketplaces>
- <https://code.claude.com/docs/en/plugin-dependencies>
- <https://code.claude.com/docs/en/discover-plugins>
**Status:** Complete

---

## 1. Marketplace = `.claude-plugin/marketplace.json` at a repo root

```json
{
  "name": "company-tools",
  "owner": { "name": "DevTools Team", "email": "devtools@example.com" },
  "metadata": { "pluginRoot": "./plugins" },
  "allowCrossMarketplaceDependenciesOn": ["other-marketplace"],
  "plugins": [
    {
      "name": "code-formatter",
      "source": "./plugins/formatter",
      "description": "Automatic code formatting on save",
      "version": "2.1.0"
    },
    {
      "name": "deployment-tools",
      "source": { "source": "github", "repo": "company/deploy-plugin" }
    }
  ]
}
```

| Field | Required | Notes |
|---|---|---|
| `name` | yes | kebab-case. Public-facing: appears in `/plugin install foo@<name>` |
| `owner` | yes | `name` required, `email` optional |
| `plugins` | yes | Array of plugin entries |
| `metadata.pluginRoot` | no | Base directory prepended to relative plugin sources |
| `allowCrossMarketplaceDependenciesOn` | no | Whitelist for cross-marketplace deps |

**Reserved marketplace names** (cannot be used by third parties): `claude-code-marketplace`, `claude-code-plugins`, `claude-plugins-official`, `anthropic-marketplace`, `anthropic-plugins`, `agent-skills`, `anthropic-agent-skills`, `knowledge-work-plugins`, `life-sciences`. Names that impersonate (e.g., `official-claude-plugins`) are also blocked. Worth knowing for naming: `ironops-marketplace` or similar is safe.

## 2. Plugin sources (the `source` field on each plugin entry)

| Source | Fields | Use case |
|---|---|---|
| Relative path | string `"./my-plugin"` | Plugin lives in the same repo as the marketplace |
| `github` | `{repo, ref?, sha?}` | Public/private GitHub repo |
| `url` | `{url, ref?, sha?}` | Any git URL (GitLab, Bitbucket, self-hosted) |
| `git-subdir` | `{url, path, ref?, sha?}` | **Subdirectory of a monorepo, sparse clone** — minimizes bandwidth |
| `npm` | `{package, version?, registry?}` | npm registry (private registries allowed) |

`ref` is a branch or tag; `sha` pins to an exact commit. Both ref and sha can be used together.

## 3. Strict mode — who owns the component definitions

```json
{
  "name": "deploy-kit",
  "source": "./plugins/deploy-kit",
  "strict": false,
  "commands": ["./commands/core/", "./commands/enterprise/"],
  "agents": ["./agents/security-reviewer.md"],
  "hooks": { "PostToolUse": [...] }
}
```

| `strict` | Behavior |
|---|---|
| `true` (default) | `plugin.json` is the authority. Marketplace entry can add components on top; both merged. |
| `false` | Marketplace entry is the complete definition. If the plugin also declares components in `plugin.json`, it fails to load. |

**This is the mechanism that makes the curated-aggregator pattern first-class in Claude Code.** A marketplace can pull raw upstream files and decide which ones to expose, without modifying the upstream.

## 4. Dependencies (`plugin.json.dependencies`)

```json
"dependencies": [
  "audit-logger",                                    // any tagged version
  { "name": "secrets-vault", "version": "~2.1.0" }   // semver range
]
```

Resolved against git tags of the form `{plugin-name}--v{version}` created by `claude plugin tag --push`. Cross-marketplace deps require `allowCrossMarketplaceDependenciesOn` on the root marketplace.

Failure modes the docs name:

| Error | Meaning |
|---|---|
| `dependency-unsatisfied` | Dep not installed/disabled |
| `range-conflict` | Two plugins' version ranges cannot intersect |
| `dependency-version-unsatisfied` | Installed version outside declared range |
| `no-matching-tag` | No `{name}--v*` tag matches the range |

How constraints combine:

| Plugin A requires | Plugin B requires | Result |
|---|---|---|
| `^2.0` | `>=2.1` | Highest `2.x ≥ 2.1.0`. Both load. |
| `~2.1` | `~3.0` | Plugin B fails with `range-conflict`. A stays intact. |
| `=2.1.0` | none | Pinned at `2.1.0`; auto-update skips newer versions while A installed. |

Enabling/disabling is dependency-aware:

| Condition | Effect |
|---|---|
| Dep not installed | Enable fails; prints `claude plugin install <dep>@<marketplace>` for each |
| Dep blocked by org policy | Enable fails; names the blocked dep |
| Dep set to `false` at a higher-precedence scope | Enable fails |
| All deps installed and allowed | Enable succeeds and writes `true` for plugin + any deps not already enabled |

## 5. Distribution channels

| Channel | Mechanism | Notes |
|---|---|---|
| **Official marketplace** (`claude-plugins-official`) | Auto-added at startup. Curated by Anthropic. | Not viable for internal-only |
| **Community marketplace** (`anthropics/claude-plugins-community`) | Anthropic-screened, pinned to SHA. User opt-in. | Public — not viable for internal-only |
| **Private GitHub / GitLab / Bitbucket repo** | `/plugin marketplace add owner/repo` or full git URL | **Viable.** Auto-update needs `GITHUB_TOKEN`/`GL_TOKEN`/`BITBUCKET_TOKEN` in env at startup |
| **Self-hosted git** | Full URL | Viable for fully internal git servers |
| **Pre-seeded container** | `CLAUDE_CODE_PLUGIN_SEED_DIR=/path/to/seed` env var | **Viable for CI/airgap**. Read-only at runtime; auto-update disabled for seeded entries |
| **Direct URL to marketplace.json** | `claude plugin marketplace add https://example.com/marketplace.json` | Limited — relative-path plugin sources break in this mode; use github/url/npm sources |

### Team auto-prompt via `extraKnownMarketplaces`

Project's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "ironops": { "source": { "source": "github", "repo": "your-org/ironops-marketplace" } }
  },
  "enabledPlugins": {
    "ironops-devops@ironops": true
  }
}
```

When a teammate trusts the repo folder, Claude Code prompts them to install. Pairs with `enabledPlugins` for auto-enable.

### Managed lockdown via `strictKnownMarketplaces`

Admin (managed settings) can restrict which marketplaces users may add. Supports exact match, `hostPattern` regex (good for self-hosted git), `pathPattern` regex (filesystem). Recommended for org-wide enforcement.

### Pre-seed for CI/airgap

```
CLAUDE_CODE_PLUGIN_CACHE_DIR=/opt/claude-seed claude plugin marketplace add your-org/plugins
CLAUDE_CODE_PLUGIN_CACHE_DIR=/opt/claude-seed claude plugin install my-tool@your-plugins
# In runtime image:
export CLAUDE_CODE_PLUGIN_SEED_DIR=/opt/claude-seed
```

Behavior:

- Seed dir is read-only at runtime; auto-updates disabled.
- Seed entries take precedence over user config on every startup.
- `/plugin marketplace remove` / `update` against seeded marketplaces is blocked.
- `extraKnownMarketplaces` declaring a seeded marketplace just uses the seed copy.

## 6. Updates

- `/plugin update <plugin>@<marketplace>` — manual update.
- `/plugin marketplace update <marketplace>` — refresh catalog.
- **Auto-update at startup** — enabled by default for Anthropic marketplaces; disabled by default for third-party. Toggle per-marketplace in `/plugin` UI. Admin can force via `extraKnownMarketplaces` `autoUpdate: true`.
- Disable Claude Code auto-updater entirely with `DISABLE_AUTOUPDATER=1`; keep plugin auto-update only with `FORCE_AUTOUPDATE_PLUGINS=1`.
- Network/timeout knobs: `CLAUDE_CODE_PLUGIN_GIT_TIMEOUT_MS` (default 120000), `CLAUDE_CODE_PLUGIN_KEEP_MARKETPLACE_ON_FAILURE=1` for airgap.

## 7. Installation scopes

| Scope | Settings file | Use |
|---|---|---|
| `user` | `~/.claude/settings.json` | Personal, default |
| `project` | `.claude/settings.json` | Shared with team via VCS |
| `local` | `.claude/settings.local.json` | Personal, gitignored |
| `managed` | Managed settings | Admin-installed, read-only |

## Key External Findings

- The build-time multi-source aggregator the user described is **directly supported**: own a marketplace, list one plugin (`ironops-devops`) whose `source` is your generated plugin (relative path inside the marketplace repo, OR a separate github repo).
- For internal distribution, **a private GitHub repo containing both the marketplace JSON and the generated plugin** is the simplest viable shape. Auth via `GITHUB_TOKEN` for headless update.
- For airgap / CI runners that can't reach upstream at runtime, `CLAUDE_CODE_PLUGIN_SEED_DIR` pre-seeds the plugin cache from a build-time image. Compatible with the curated-aggregator pattern.
- Cross-plugin name collisions are not a real concern — skills are namespaced by plugin name (`/ironops-devops:troubleshoot`). Collisions within one plugin are caught by `claude plugin validate`.
- Dependencies use semver but require `{plugin-name}--v{version}` git tags. For an initial monolithic aggregator there are no inter-plugin dependencies to declare; we can revisit if we later split.

## Recommendations from External Research

- **For "internal only" + "single curated plugin":** private GitHub repo `IronbellyOrg/ironops-marketplace` containing the rendered `ironops-devops` plugin alongside `.claude-plugin/marketplace.json`. Target projects do `/plugin marketplace add IronbellyOrg/ironops-marketplace` and `/plugin install ironops-devops@ironops`.
- Use `omit-version` mode (commit SHA = update signal) for v0.1. Switch to explicit `version` once we have a release cadence.
- Builder must run `claude plugin validate` on every produced plugin before publishing.
- Provenance: write a generated `META.json` (or similar) listing each imported file's source repo, commit SHA, and source path. Plugins are caches, so this file ships *inside* the plugin; users get it.
- Hooks: defer entirely from the runtime plugin in v0.1. The plugin ships no `hooks/hooks.json`. TDD describes the future hook layout but the builder simply does not copy hook scripts until a future release.
