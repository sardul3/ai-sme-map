# Contributing

This atlas is opinionated. **Do-rail changes are a product decision.** Skim may grow from harvest diffs.

## Outlines (`scripts/outlines.py`)

- Key = **normalized** parent URL already in the catalog.
- Parts: `{slug, title, url}`. `url` may be `null` for Coursera weeks.
- Verify lesson URLs return 200 before adding them.
- Do not scrape login walls or cookies.

## Harvest

1. Run `make harvest-diff` after editing `harvest/*.md`.
2. New URLs default to **Skim**, not Do.
3. Changing `scripts/graph_spec.py` station `do:` lists requires scorecard evidence in the PR (intuition, exercises, modern stack, SME depth).
4. Commute rows live in `scripts/commute.py`. Human-gated: teaching enclosures only (15–45 min, T0–T5 `station_id`, direct `audio_url`). No news, interviews, YouTube-only, or harvest auto-add.

## Pull requests

- `make validate` must pass.
- Do not add secrets, `.env`, or progress dumps with personal notes you would not commit.
- Codeowners: `scripts/graph_spec.py`, `scripts/outlines.py`.
