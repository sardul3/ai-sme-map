# ADR 0001 — Distribution surface

Date: 2026-09-12
Status: accepted (Q31: public GitHub + Pages)

## Context

E8 asked how a second person uses the atlas without a public writable PUT.

## Options

1. Private git clone + localhost `make serve` (status quo).
2. Public GitHub + same localhost server.
3. Static host + `localStorage` progress (no PUT on the internet).

## Decision

**Ship option 3 for the public copy, keep option 1 for the authoring loop.**

- `make serve` stays loopback-only. PUT `/data/progress.json` is 403 off localhost.
- GitHub Actions compiles the catalog, runs `export_static.py`, and deploys a flat `dist/` to GitHub Pages.
- The public bundle ships `{schema_version: 1}` only. Browser progress is `localStorage` (`atlas_progress`).
- Homepage links to `commute.html` so the eyes-off playlist and harvest library are not dumped under Tonight.

## Consequences

- No accounts (E12 stays later).
- No telemetry unless the user enables the local eval log.
- Do not bind `0.0.0.0`.
- Public site: https://sardul3.github.io/ai-sme-map/
