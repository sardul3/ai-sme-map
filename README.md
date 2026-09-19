# AI/ML SME Atlas

Dual-rail map of becoming an AI/ML subject-matter expert. **Python 3.12+**, zero third-party packages. Authoring is localhost; the public copy is static GitHub Pages.

Resources are ranked by **intuition, exercises, modern stack, leftover SME depth** — not by institution. The catalog is large so a gem cannot hide. You only *Do* the ranked rail. **Focus** is tonight’s lesson (or the first Do item). Parallel and Skim stay collapsed; T2–T7 start folded.

**This is not** a degree, not 1,242 homework items, not dealradar, and not a hosted app. Progress is a local file. Do not put the PUT endpoint on a public IP.

**61 stations** across T0–T7. The builder fork (Claude Code, LangGraph, MCP) sits at T3 after classical ML so those prereqs are met. Local: [http://127.0.0.1:7432](http://127.0.0.1:7432). Public static copy: [https://sardul3.github.io/ai-sme-map/](https://sardul3.github.io/ai-sme-map/) (progress in `localStorage`; no public PUT). Agent catalog (title + url, every unique learning URL including lesson parts): [data/links.json](https://sardul3.github.io/ai-sme-map/data/links.json).

## Run (supported path)

```bash
cd ~/dev/ai-sme-map
python3 --version   # 3.12+
make validate
make serve          # http://127.0.0.1:7432
```

If the port is in use, unload the optional macOS agent:

```bash
make uninstall-agent
```

macOS auto-start is optional: `make install-agent`.

Linux smoke without installing Python 3.12 on the host: `docker build -t ai-sme-map .` (validate-only; the image does not serve).

**Progress:** `data/progress.json`. Copy it before a risky compile: `make backup-progress`. Keys starting with `r-` are resources; `schema_version` is metadata. Second machine: `docs/SYNC.md` then `make sync-check`.

**Catalog freshness:** `make harvest-diff` after editing harvest files. `make links-do` checks Do + lesson URLs (needs network; fails only on 404/410). See `harvest/SOURCES.md`. Do-rail changes need a human (`CONTRIBUTING.md`).

Local eval log (opt-in, no PII sent anywhere): in the browser console, `localStorage.setItem('atlas_eval','1')`. Events stay in `localStorage`. Paste that JSON to `data/eval_log.json` and run `make eval-slo`.

Keyboard: `d` marks the current Focus lesson done. Space play/pauses the commute player when it is open.

**Commute · eyes-off** (`commute.html`) ranks walk-time audio by purpose — Learn, Hear people, Ship, Stay current — not by Tonight’s lesson stations. Talking Machines, Data Skeptic, Practical AI, TWIML, and Latent Space sit on those rails with the teaching shows. The deck player has prev/next, ±15s, a scrubber with times, and speed. Playback position lives in `localStorage` (`atlas_commute_pos`). Ticks do not count as Do.

**Library · unassigned** (`library.html`) is everything cataloged that is on neither track, grouped by harvest file or curated kind. A Monday GitHub Action refetches pinned awesome-lists and commute RSS, compiles, and opens a PR. New harvest URLs land here. New enclosures land in `data/inbox.json` until someone copies them into `scripts/commute.py`. Tonight Do rails are never auto-edited.

`data/feed.xml` is a **personal, unpublished** playlist of those original enclosures. Do not submit it to Apple Podcasts or treat it as a public SME Atlas show.

License: MIT for **code**. Catalog is links — `ATTRIBUTION.md`.
