# Phase 7 Validate Smoke Summary

## Commands

| Command | Exit Code |
|---|---|
| `uv run ironops build --manifest <test-manifest> --staging /tmp/staging --dry-run --verbose` | 0 |
| `claude plugin validate /tmp/staging` (via Stage 5 wrapper) | 0 |

## Notes

- The v0.1 production manifest at `/config/workspace/IronOps/manifest.yaml`
  declares `git@github.com:IronbellyOrg/IronClaude.git` as its source, which
  requires GitHub SSH access not available in this environment. The smoke
  build was therefore run against a hermetic manifest pointing at a local
  `file:///` clone of `tests/fixtures/ironclaude-snapshot/` — same builder
  code paths, just a different upstream URL.
- During this validation a real `claude plugin validate` warning surfaced
  ("No marketplace description provided"), which (by NFR-4 strict-warnings)
  failed the build. The metadata emitter was updated to populate a default
  `description` field on `marketplace.json` so the validator emits no
  warnings on a clean build.

## Pipeline trace

```
[ironops] stage 0: preflight
[ironops] stage 2: read manifest
[ironops] stage 1: clone
[ironops] stage 3: render
[ironops] stage 4: write metadata
[ironops] stage 5: validate
[ironops] stage 6: publish
[ironops] stage 6: skipped (dry_run)
[ironops] stage 7: report
plugin=ironops-devops-test files=10 sources=ironclaude@861e40ac publish=skipped(dry_run)
```

## Verdict

**PASS** — full end-to-end pipeline succeeds against a hermetic upstream;
`claude plugin validate` exits 0 with no warnings.
