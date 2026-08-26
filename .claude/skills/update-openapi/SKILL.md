---
name: update-openapi
description: Use when asked to update, refresh, sync, or bump openapi.json or the OpenAPI/partner-service spec in this repo, or when a new spec version needs to be pulled into the docs.
---

# Updating openapi.json

## Overview

`openapi.json` is a **generated artifact** — never save the raw export into the repo. The raw spec at `https://api.explorium.ai/openapi.json` carries `"default"` keys that break Mintlify's playground rendering and internal `marked_for_null_replacement` markers that must become `"example": null`.

## The one command

```bash
python3 scripts/update_openapi.py
```

It fetches the prod export, applies the required transformations, and refuses to write if any operation referenced by page frontmatter would disappear (this once happened: a v1-only export silently deleted every `/v2` playground).

## Reading its report

| Report line | What to do |
| :--- | :--- |
| `added: [...]` | Each new operation needs a reference page + `docs.json` nav entry, following the existing per-group pattern |
| `removed: [...]` | Confirm intentional; remove/repoint the affected pages |
| `BLOCKED` | A documented operation vanished from the export — investigate before considering `--force` |

## After it writes

1. `mint openapi-check openapi.json` — must pass
2. `mint broken-links` — expect only the pre-existing failures
3. Check whether schema changes contradict page prose (field tables, examples)
4. Ship via the repo convention: branch → PR → squash merge

## Red flags — stop

- `curl .../openapi.json > openapi.json` or hand-saving the export from a browser
- "The raw spec is close enough" — 37 defaults + 68 markers were in the last raw export
- Bypassing a `BLOCKED` result with `--force` without checking which pages break
