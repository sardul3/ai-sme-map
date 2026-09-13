# Blockers (loop)

Documented and skipped so later epics could proceed. The loop does **not** stop on these.

| ID | Item | Why skipped | Next |
|---|---|---|---|
| B1 | Confirm Focus in a real browser | No browser automation in this agent session | Hard-refresh http://127.0.0.1:7432 and Mark done on Vectors |
| B2 | First-run screenshot / 20s recording (E4) | Same as B1 | Capture after B1 |
| B3 | Nightly CI runner for `make links-do` | **Shipped** (`.github/workflows/atlas.yml`) | Watch first scheduled run |
| B4 | Real `git_sha` | Repo has no commits yet; stamp is `uncommitted` | Appears after the first commit |
| B5 | Score every Do winner (E6) | Time; first sixty unique Do scored + `ranking_pass` date | Quarterly scorecard pass |
| B6 | ~~5-question placement quiz~~ | **Shipped** (`data/placement.json` + UI) | — |
| B7 | arXiv RSS fetcher (E2) | Cadence documented; live fetch not built | Manual quarterly Skim |
| B8 | Public GitHub | **Shipped** (Pages + Actions) | Confirm https://sardul3.github.io/ai-sme-map/ |
| B9 | Linux Docker smoke (E4) | Try `docker build` when Docker.app is running | Friend install on Linux |
| B10 | E12 accounts | Explicitly later in ADR 0001 | Syncthing of progress.json (`make sync-check`) |
| B11 | Restart LaunchAgent after every serve.py edit | Future edits need it again | `launchctl kickstart -k gui/$(id -u)/com.sagar.ai-sme-map` |
| B12 | Full `make links` on featured URLs | Network-heavy | `make links` when idle |
| B13 | Sutton & Barto HTML (`incompleteideas.net`) | DNS/URLError from this network; not a proven 404 | Keep Do URL; warn not fail |
| B14 | DeepLearning.AI short course HTTP 500 / Neel Nanda 429 | Upstream flaky | Warn not fail; recheck later |

If a blocker is lifted, tick the matching epic in `epic-status.md`.
