# Authoring an IronOps Manifest

This guide is for UC-2 release engineers maintaining the v0.1 manifest.

## Schema

```yaml
schema_version: "1"   # string, not int — FR-14 hard-fails on int 1

sources:
  <source-id>:
    url: "git@github.com:Owner/Repo.git"
    ref:  "develop"   # optional — defaults to remote HEAD (FR-2)
    sha:  "<40-hex>"  # optional, mutually exclusive with ref

imports:
  - source:   "<source-id>"
    from:     "src/path/in/upstream.md"   # or trailing-slash for directory
    to:       "agents/file.md"             # destination relative to plugin root
    kind:     "agent"                      # one of: agent | skill | command | template | script | other
    requires: ["skills/sc-foo-protocol/"]  # FR-4 co-import declarations (optional)

plugin:
  name:        "ironops-devops"           # kebab-case enforced
  description: "..."

marketplace:
  name:  "ironops"
  owner: { name: "IronbellyOrg" }
```

## kind enum

| Kind | Use |
|---|---|
| `agent` | Standalone agent persona markdown |
| `skill` | Skill directory (SKILL.md + refs/) |
| `command` | Slash command markdown |
| `template` | Template fixture |
| `script` | Helper script |
| `other` | Anything not covered above |
| `hook-config` | **RESERVED in v0.1** — rejected by builder |
| `hook-script` | **RESERVED in v0.1** — rejected by builder |

## `requires:` (FR-4 co-import)

When a command file body contains `Skill sc:<x>-protocol`, the matching
skill directory MUST be imported. Declare the dependency via `requires:`.
Co-import scanning runs at render time; missing companion skills raise
`CoImportMissing` (exit 12) with a message naming both the orphan skill
and the citing command.

The reverse direction (skill imported without a citing command) emits
a warning, not a failure (FR-4-A2).

## Full annotated example

```yaml
schema_version: "1"

sources:
  ironclaude:
    url: "git@github.com:IronbellyOrg/IronClaude.git"
    # ref omitted → resolved at build time via `git ls-remote --symref`

imports:
  - source: ironclaude
    from:   "src/superclaude/skills/sc-troubleshoot-protocol/"
    to:     "skills/sc-troubleshoot-protocol/"
    kind:   skill

  - source: ironclaude
    from:   "src/superclaude/commands/troubleshoot.md"
    to:     "commands/troubleshoot.md"
    kind:   command
    requires:
      - "skills/sc-troubleshoot-protocol/"

plugin:
  name: "ironops-devops"
  description: "DevOps plugin."

marketplace:
  name: "ironops"
  owner: { name: "IronbellyOrg" }
```

## Common pitfalls

1. **Self-overwrite (FR-16)** — `to:` MUST NOT target one of the generated
   paths: `.claude-plugin/plugin.json`, `META.json`, `THIRD_PARTY_LICENSES.md`.
2. **Orphan command (FR-4)** — A command referencing `Skill sc:foo-protocol`
   without the matching skill import = build fails with `CO_IMPORT_MISSING`.
3. **Reserved kind in v0.1 (§11)** — `hook-config` and `hook-script` are
   reserved; using them = `MANIFEST_INVALID`.
4. **`schema_version: 1`** (int) — must be the string `"1"`. Common YAML
   gotcha — wrap in quotes.
5. **Plugin name not kebab-case** — `IronOps_DevOps` is rejected;
   `ironops-devops` is accepted.

## NFR-3 enforcement — always-on context budget

Per disposition D8 the rendered plugin tree should keep total always-on
context below ~1500 tokens. Skills and agents loaded on-demand do not
count toward the always-on budget. To measure after install:

```bash
claude plugin install IronbellyOrg/ironops-marketplace/ironops-devops
claude plugin details ironops-devops
```

Inspect the "always-on context" column. If it exceeds 1500 tokens, audit
the imports for files that should be loaded on-demand instead of
always-on (e.g., reference material that belongs under a skill's `refs/`
subdirectory rather than at the agent level).
