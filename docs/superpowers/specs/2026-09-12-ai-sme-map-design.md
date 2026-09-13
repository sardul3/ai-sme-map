# AI/ML SME Atlas — Design

Date: 2026-09-12
Status: approved (“lets go”)

## Goal

A private, always-on localhost map that ranks resources by pedagogy (not institution), lists ≥500 unique learning URLs so gems cannot hide, and tracks progress in git.

## Non-goals

- Not part of dealradar.
- Not a roadmap.sh official PR as source of truth (optional later export).
- Not “complete 500 courses.” Completing a node means finishing its `do` rail.
- No scraping employer cookies.

## Ranking scorecard (same for every resource)

1. Intuition / visual pedagogy
2. Completeness for that lesson
3. Forced exercises
4. Modern stack
5. Leftover value at SME depth

NPTEL/IISc is one harvest among many. It never starts in first place.

## Architecture

| File | Role |
|---|---|
| `harvest/*.md` | Sourced awesome lists, paper roadmaps, course indexes |
| `scripts/compile_catalog.py` | Parse + curated winners → `data/resources.json` + `data/graph.json` |
| `data/progress.json` | Per-resource status: todo / doing / skimmed / done |
| `web/` | Dual-rail station map |
| `scripts/serve.py` | Static files + PUT progress on `127.0.0.1:7432` |
| `launchd/` | Start server on login; open browser once |

## Pedagogy shape

Stages 0–7 as a **double rail**: theory strand and practice strand. Each station has `do`, `parallel`, `skim`, `project`. At 15h/week, year 1 is stages 0–5.

## Catalog floor

`len(unique normalized URLs) >= 500` after compile. Harvests include Coursera/Pluralsight-shaped public pages, university lecture series, NPTEL, books, papers, free gem series.

## UI

Transit-timetable atlas (cool gray paper, navy ink, orange theory line, cerulean practice line). Map of stations, not a 500-row table. Search opens a drawer.

## Success

- `python3 scripts/validate.py` passes (≥500 unique http(s) URLs).
- Opening `http://127.0.0.1:7432` renders the map from JSON with no blank state.
- Progress survives reload via `data/progress.json`.
