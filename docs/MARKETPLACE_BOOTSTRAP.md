# Marketplace Repo Bootstrap

This guide documents the one-time setup for the
`IronbellyOrg/ironops-marketplace` private GitHub repo that IronOps
publishes to. Per OQ-3 the marketplace repo is created manually
(not by the builder).

## 1. Create the private repo

```bash
gh repo create IronbellyOrg/ironops-marketplace --private \
  --description "Private Claude Code marketplace for ironops-devops plugin"
gh repo clone IronbellyOrg/ironops-marketplace
cd ironops-marketplace
```

## 2. Initial commit

```bash
mkdir -p .claude-plugin
cat > .claude-plugin/marketplace.json <<'JSON'
{
  "name": "ironops",
  "owner": { "name": "IronbellyOrg" },
  "plugins": []
}
JSON

cat > README.md <<'MD'
# IronOps Marketplace

Private Claude Code marketplace populated by the IronOps builder.
This repo is mirror-managed by `IronbellyOrg/IronOps` — do not edit
`plugins/` or `.claude-plugin/marketplace.json` by hand.
MD

git add -A
git commit -m "bootstrap marketplace repo"
git push origin main
```

## 3. CI auth (OQ-4)

The publishing workflow (`.github/workflows/build-publish.yml`)
authenticates against the marketplace repo using a PAT stored as the
`IRONOPS_MARKETPLACE_TOKEN` secret on the IronOps repo:

```bash
# Generate a fine-scoped PAT with `repo` scope on the marketplace org
gh secret set IRONOPS_MARKETPLACE_TOKEN \
  --repo IronbellyOrg/IronOps \
  --body "<paste PAT here>"
```

The PAT scope is `repo` (full read/write to the single marketplace repo).
Do NOT use a token with broader scope.

## 4. First-build verification

After the secret is configured:

1. Trigger the build workflow manually:
   ```bash
   gh workflow run build-publish.yml --repo IronbellyOrg/IronOps
   ```
2. Watch the run and confirm exit 0.
3. Switch to the marketplace repo and verify the new commit:
   ```bash
   cd ironops-marketplace && git pull
   git log -1 --oneline
   ls plugins/ironops-devops/
   ```
4. From a target developer machine, install:
   ```bash
   claude plugin marketplace add IronbellyOrg/ironops-marketplace
   claude plugin install ironops-devops
   claude plugin details ironops-devops
   ```

## Failure recovery

If the build fails partway, the marketplace HEAD is unchanged (FR-9).
Re-run the workflow after addressing the root cause; no manual cleanup
of the marketplace repo is required.
