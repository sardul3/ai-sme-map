# Epic status (loop 2026-09-12, all twelve visited)

| Epic | Status | Notes |
|---|---|---|
| E1 Lesson-level Focus | **done + more outlines** | Plus 6.042J lectures 1–7, CS188 slug projects, HF agents units. |
| E2 Catalog flywheel | **done with gaps** | Do 404s repaired (Yan evals, Neal course, bandit PDF, sktime www). `make links-do` fails CI only on 404/410. `last_ok` in `link_status.json`. Nightly workflow on GitHub Actions. |
| E3 Trust, license, localhost | **done** | MIT, ATTRIBUTION, libgen deny, loopback PUT 403. |
| E4 Second-person install | **done with gaps** | `make serve`, Python 3.12, Dockerfile validate-only, `git uncommitted` stamp. No screenshot (B2). Linux Docker not executed on this Mac unless `docker` is present. |
| E5 Progress portability | **done** | schema_version, backup/import/export. |
| E6 Ranking transparency | **done (first 60 Do)** | scores on first sixty unique Do. Rest of Do rail unscored (B5). |
| E7 Beginner UX remainder | **done (minimal)** | Sticky Focus, undo, sittings, skip, aria-labels on status/Focus, stale badge, `.meta-line` CSS restored. Browser confirm still B1. |
| E8 Distribution surface | **done** | Public GitHub + Pages (`export_static`, `localStorage`). Loopback PUT unchanged. |
| E9 Placement / skip-ahead | **done** | Skip button + five checkbox questions in `data/placement.json`. |
| E10 Contributions | **done (docs)** | CONTRIBUTING, CODEOWNERS, templates, CoC. No live remote. |
| E11 Map quality evals | **done (local SLO)** | opt-in localStorage log; `make eval-slo` on pasted `data/eval_log.json`; Do 404 SLO. |
| E12 Identity and sync | **visited, deferred accounts** | `docs/SYNC.md` + `make sync-check`. No accounts. |

## Immediate needs

1. Browser confirm Focus Open + Mark done — **blocked** (B1).
2. First git commit so `git_sha` is a real hash (B4).
3. Confirm Pages URL after first Actions deploy (B8).
