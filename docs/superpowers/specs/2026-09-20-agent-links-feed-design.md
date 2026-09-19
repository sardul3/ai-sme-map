# Agent links feed — Design

Date: 2026-09-20
Status: approved in chat (scope B; approach 1; wrapper `atlas.links.v1`)

## Goal

Publish one lean JSON file of every unique learning URL in the compiled catalog (parent records plus nested lesson `parts` that have a URL) so humans can fetch it from the site and agents can ingest it as the agent-facing catalog contract.

Public URL: `https://sardul3.github.io/ai-sme-map/data/links.json`  
Local URL: `http://127.0.0.1:7432/data/links.json`

## Locked decisions

- Scope B: flatten parent + `parts[]` URLs. Skip `url: null` parts. Inbox RSS is out until it is human-gated into the catalog.
- Approach 1: compile-time projection. Harvest markdown + curated Python remain the authoring source of truth. Fat `data/resources.json` remains the UI catalog. `data/links.json` is the agent-facing contract and must be rewritten on every `compile_catalog.py` run.
- Wrapper object, not a bare array. Schema id `atlas.links.v1`.
- Item fields are `title` and `url` only. “Link” in the request maps to `url` so agents match the rest of the catalog.
- Do not include `id`, scores, outlines, `audio_url`, progress, or inbox rows.
- Tonight / Commute / Library / Roadmap keep fetching fat `resources.json`. They do not switch to the lean file.
- Homepage gets a static `<a href="data/links.json">` so the feed is findable without running JS.
- Python 3.12+, stdlib only. No new npm packages.

## Non-goals

- Replacing or slimming `resources.json`.
- Feeding `data/inbox.json` commute candidates.
- Emitting enclosure/`audio_url` rows.
- `llms.txt`, robots, or a second agent format.
- Changing ranking, Do rails, or harvest parsing.
- Accounts, hosted PUT, or binding `0.0.0.0`.

## Why this is the right size

`resources.json` is already on Pages (~1,453 records plus outline extras) but it is too fat for agent context. Outline lessons with unique URLs are already upserted into `resources.json`; flattening `parts[]` is still the contract so a part URL cannot hide on the parent. Compile writes both files in one pass so they cannot drift.

---

## 1. File and schema

`scripts/compile_catalog.py` writes `data/links.json` next to `resources.json`.

```json
{
  "schema": "atlas.links.v1",
  "compiled_at": "2026-09-17T02:17:22Z",
  "git_sha": "78ab880",
  "count": 1602,
  "items": [
    {"title": "3D Gaussian Splatting", "url": "https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting"}
  ]
}
```

- `compiled_at` and `git_sha` are the same strings written into `catalog_meta.json` on that compile.
- `count` equals `len(items)` and is also stored as `links_count` on `catalog_meta.json`.
- `items` is a JSON array of objects. Each object has exactly the keys `title` and `url`.
- `title` is the catalog title (strip, max 180 chars — same as upsert).
- `url` is the **normalized** http(s) URL (same `normalize()` as the rest of compile).
- Sort `items` by `title` case-insensitive, then `url`, so the file is stable across compiles.
- Pretty-print with indent 2 and a trailing newline, same as other catalog JSON.

Version policy: additive only on `atlas.links.v1`. A breaking change (rename `url`, drop the wrapper, change uniqueness) requires `atlas.links.v2` and keeping v1 until a later removal.

## 2. Flatten rules

Pure function `lean_links(resources) -> list[dict]` in `scripts/compile_catalog.py`. Input is the compiled `resources` list after `attach_outlines`.

For each resource, in catalog order:

1. If `resource["url"]` is a non-empty string, candidate `(title, url)`.
2. For each entry in `resource.get("parts") or []`, if `part["url"]` is a non-empty string, candidate `(part title, part url)`.

Then:

- Run each URL through `normalize()`. Skip a candidate if normalize raises or the result does not start with `http`.
- Unique by normalized URL. First title wins (parent is visited before its parts, so a repeated part URL keeps the earlier row).
- Do not read `audio_url`, `inbox.json`, or `feed.xml`.

`count` equals `len(items)` after unique. Outline lessons with URLs are already extra rows in `resources.json`; flattening `parts[]` must not drop those URLs and must not invent inbox URLs. Equality with `len(resources)` is allowed when every catalog row already has a distinct URL.

## 3. Hosting

`scripts/export_static.py` `DATA_FILES` gains `"links.json"`. GitHub Pages already deploys `dist/`, so the public path is `/data/links.json` (repo Pages base ` /ai-sme-map/` is already handled by `dataHref` / relative links).

`scripts/serve.py` already serves `/data/*.json` from the data dir; no new route.

Missing `links.json` after compile is a validate failure, not a silent skip.

## 4. Homepage discoverability

In `web/index.html`, next to `#meta`, a static relative link:

```html
<p class="meta-line" id="meta"></p>
<p class="meta-line"><a href="data/links.json">Agent links</a> · title + url · every catalog URL</p>
```

Do not put this inside `paintCounts` (`textContent` would strip markup). Library / Commute / Roadmap do not need the link in v1.

## 5. Testing

Stdlib `unittest`, matching existing tests.

- Unit: given one parent, one part with a URL, one part with `url: None`, and a second parent that repeats the part URL, `lean_links` returns two items (parent + unique part), omits the null part, first title wins on the duplicate.
- Compile/export: `data/links.json` exists after compile; `schema` is `atlas.links.v1`; `count == len(items)`; every item has exactly `{title, url}`; every `url` starts with `http`; no duplicate URLs; `export_static` copies the file into `dist/data/links.json`.
- Validate: fail if the file is missing, schema mismatches, `count` mismatches, an item has extra keys, or an item URL is absent from the flatten of the current `resources.json`.
- Static HTML: `index.html` contains `href="data/links.json"`.

Success: `make validate` passes; `curl -sI http://127.0.0.1:7432/data/links.json` is 200 locally after `make serve`; after merge to `main`, Pages serves `https://sardul3.github.io/ai-sme-map/data/links.json`.
