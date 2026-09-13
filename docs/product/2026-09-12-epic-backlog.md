# SME Atlas — Product backlog for PM / PO

Date: 2026-09-12
Status: working draft from current localhost atlas (1,242 resources, 59 stations, Focus = station `do[0]`)
Audience: product manager, product owner, implementing agents

**Product outcome:** a beginner can finish tonight’s sitting, trust the ranking, and a second person can install the atlas without inheriting a private LaunchAgent. Catalog does not rot.

Locked from prior decisions (do not reopen in epic grooming unless the user reverses them):

- Scorecard over institution. NPTEL does not start first.
- Completing a station ≠ completing the catalog. Focus = first Do item (later: first unfinished lesson).
- Containment-only duplicates (parent/part). No “Ng covers StatQuest” substitutes in v1.
- Catalog floor ≥500 unique URLs so gems cannot hide. Skim is a library, not homework.
- Not part of dealradar. No employer-cookie scraping. roadmap.sh is a later export, not source of truth.
- Search stays. No extra Coursera-only chip.

---

## Immediate needs (this week)

Do these before opening E8 (public host) or E10 (community). They are slices, not whole epics.

1. **Confirm Focus in a real browser** — Open 3Blue1Brown from the ticket; Mark done; Focus must move to Work matrices. If it does not, that is a P0 bug, not a new epic.
2. **Ship lesson outlines for the beginner path** — T0 Essence of LA videos, then Imperial/Ng slug-weeks, then fast.ai lessons. Engine already specified in `docs/superpowers/specs/2026-09-12-next-lesson-design.md`.
3. **Stamp the catalog** — Show `compiled_at` and harvest count on the atlas. A stranger must see how old the map is.
4. **Dead-link smoke on Do + Focus URLs** — CI or `make links` on ~100 Do URLs. A distributed map with 404s on “start here” is unusable.
5. **LICENSE + harvest attribution** — Cannot put the repo on GitHub until awesome-list licenses and AIMA/course pages are attributed.
6. **Progress backup** — One-line README: progress is `data/progress.json`; copy it before `make compile`. Optional `make backup-progress`.
7. **Bind-address audit** — Document and test that PUT `/data/progress.json` is localhost-only. Distributable means we do not accidentally listen on `0.0.0.0`.
8. **Sitting strings for remaining T0–T1 Do[1] items** — ISL, CS188, AIMA, etc. First ten primaries already have `sitting`.
9. **Install path that is not LaunchAgent** — `make serve` + Python 3.12 documented for macOS/Linux; LaunchAgent optional.
10. **Write a one-page “how the catalog is refreshed”** — Pin this doc’s Catalog flywheel in README. Process before automation.

Rank: 1–2 are learner-facing; 3–7 are the minimum to hand the repo to anyone else; 8–10 are cheap and prevent rework.

---

## Ranked epics

Priority is **learner value × can we distribute × irreversibility**. Effort is calendar weeks for one engineer who already knows this repo. Tasks are the enclosed backlog; they become stories after the PM/PO answers the questions in that epic’s cluster.

### Rank 1 — E1 Lesson-level Focus

**Outcome:** Tonight’s unit is a lesson, not a 40-hour course.  
**Why now:** Focus exists but still completes a whole listing. That was the agreed next product build.  
**Depends on:** none. **Unblocks:** honest sitting times, placement later.  
**Questions to answer first:** Q12, Q13, Q28, Q29.

Tasks:

- [ ] Compile `parts` from `scripts/outlines.py`; slug-only weeks allowed (`url: null`).
- [ ] Roll up: parent done covers parts; last part done marks parent; un-tick part un-dones parent.
- [ ] Focus picker walks `do[0]` parts, then next station (later Do items do not block).
- [ ] Seed 3Blue1Brown Essence of LA from live TOC (drop 404s).
- [ ] Seed fast.ai lesson pages that return 200.
- [ ] Seed Ng spec + Imperial LA as slug-only weeks.
- [ ] Drawer nested checklist; Focus Open hits lesson URL or parent fallback.
- [ ] Search hit that is a child shows “lesson of {parent}” / “covered by” when parent is done.
- [ ] Unit tests for `next_focus` / `apply_status`; `make validate` still ≥500 unique HTTP URLs.
- [ ] Restart LaunchAgent after `serve.py` changes if Focus is served as JSON.

### Rank 2 — E2 Catalog flywheel

**Outcome:** The map’s age is visible; refresh is a repeatable job with a human gate on Do-rail changes.  
**Why now:** 1,242 URLs will rot; harvest markdown is a snapshot. Distribution without a flywheel ships a museum.  
**Depends on:** E3 attribution so we know what we may refetch. Can start link-check in parallel.  
**Questions:** Q19–Q26, Q45.

Tasks:

- [ ] Record upstream harvest source URL + retrieved date + license in each `harvest/*.md` header.
- [ ] Pin content hashes of harvest files; `make harvest-diff` shows added/removed URLs.
- [ ] `make links` checks Do + Focus + featured URLs; fail CI on 404/410 for those rails only.
- [ ] Write `compiled_at` into `graph.json`; show it in the UI kicker.
- [ ] Changelog: resources added/removed/moved between rails (Do vs Skim).
- [ ] Policy: harvest may grow Skim automatically; **Do-rail edits require a human** (PR checklist).
- [ ] Quarterly scorecard pass on T0–T3 Do winners (stack age: course edition, library).
- [ ] Lightweight new-paper intake: one arXiv RSS or “papers we already curated” re-check per branch, not a full scrape.
- [ ] Stale badge: featured resource with `last_ok` older than 90 days.
- [ ] Document non-goals: no Coursera/YouTube TOC scrape, no cookie harvest.

### Rank 3 — E3 Trust, license, localhost

**Outcome:** A public or shared git remote does not create copyright or security incidents.  
**Why now:** Hard to reverse once the repo is cloned. Blocks E8/E10.  
**Questions:** Q37–Q42, Q48.

Tasks:

- [ ] Choose SPDX license for *code* (likely MIT or Apache-2.0).
- [ ] Separate catalog license / ToS: harvested lists are not our copyright; keep pointers + short quotes only.
- [ ] `ATTRIBUTION.md` for awesome-* lists, AIMA, course sites.
- [ ] Confirm serve.py binds `127.0.0.1`; add a test that refuses non-loopback PUT if we ever change host.
- [ ] No secrets in repo; `.gitignore` for `.env`, checkpoint pickles if any.
- [ ] Harvest deny-list: social, badges (already), plus scraped login walls.
- [ ] README “what this is not” (not a degree, not 1,242 homework items, not dealradar).
- [ ] Security note: progress file is local; do not host PUT on a public IP.
- [ ] Decide trademark use of “Coursera”, “Stanford”, etc. in UI (nominative fair use vs logos).

### Rank 4 — E4 Second-person install

**Outcome:** A Python engineer clones, runs `make validate && make serve`, and sees Focus without macOS LaunchAgent.  
**Why now:** “Distributable” starts at install, not at marketing.  
**Questions:** Q31–Q36.

Tasks:

- [ ] Pin Python 3.12+ in README; zero third-party deps remains the default.
- [ ] `make serve` documented as the supported path; LaunchAgent optional macOS extra.
- [ ] Port-in-use message with how to stop the agent / change port.
- [ ] Linux smoke (even if in Docker) for `scripts/serve.py`.
- [ ] First-run: empty progress, Focus = Essence of LA, T2–T7 collapsed.
- [ ] Screenshot or 20s screen recording of first sitting.
- [ ] `CONTRIBUTING.md` for outlines and harvest PRs (even if repo stays private).
- [ ] Issue templates: dead link, wrong ranking, new station request.
- [ ] Version or git SHA in the UI footer.

### Rank 5 — E5 Progress portability

**Outcome:** Progress survives compile, machine change, and schema adds (`parts`, `sitting`).  
**Questions:** Q27–Q30.

Tasks:

- [ ] `schema_version` in `progress.json`.
- [ ] `make backup-progress` copies a timestamped file.
- [ ] Import/export a single JSON; never overwrite without backup.
- [ ] Compile must not delete unknown progress keys.
- [ ] Migration notes when part ids appear.
- [ ] Optional git commit hook reminder (do not auto-commit secrets).

### Rank 6 — E6 Ranking transparency

**Outcome:** A beginner sees *why* this Do beat the skim list, using the five-point scorecard.  
**Questions:** Q14–Q18.

Tasks:

- [ ] Store optional `scores: {intuition, exercises, stack, depth}` on featured Do items (human, not model-invented).
- [ ] UI: one line under evidence, “Ranked for intuition + exercises.”
- [ ] Date of last ranking pass per station.
- [ ] “Why not NPTEL here” only when an NPTEL item is on Parallel/Skim of that station (no institution bashing elsewhere).
- [ ] Rubric in README matching the design spec.

### Rank 7 — E7 Beginner UX remainder

**Outcome:** The first evening still works on a laptop at 900px, with keyboard, without staff vocabulary.  
**Questions:** Q8–Q11, Q47.

Tasks:

- [ ] Keyboard: mark Focus done, jump Next, expand later stages.
- [ ] Focus strip contrast / reduced-motion (respect `prefers-reduced-motion` for smooth scroll).
- [ ] Sitting on all year-1 Do items, not only the first ten primaries.
- [ ] Undo last status (one-level).
- [ ] Drawer does not bury Focus below a long map on small heights (sticky Focus).
- [ ] Screen-reader name for status buttons.
- [ ] Empty Focus complete state already exists; add “reopen last station.”

### Rank 8 — E8 Distribution surface

**Outcome:** People who are not on this Mac can use the atlas without a public writeable PUT.  
**Questions:** Q31, Q33, Q35, Q36, Q43.

Tasks:

- [ ] Decide: git clone (private), GitHub public, or static pages + localStorage.
- [ ] If static: progress in localStorage; no PUT on the internet.
- [ ] Privacy page: no telemetry unless E11 opt-in.
- [ ] Freeze a release tarball of `data/*.json` + `web/`.
- [ ] roadmap.sh export remains optional and sanitized.

### Rank 9 — E9 Placement / skip-ahead

**Outcome:** A Python engineer who already knows LA is not forced through 3Blue1Brown to reach Ng.  
**Questions:** Q9, Q10, Q46.

Tasks:

- [ ] “I already know this station” marks primary Do done (Focus advances) without faking lesson ticks.
- [ ] Optional 5-question placement (LA, calc, sklearn, backprop, git).
- [ ] Do not skip eval/search stations by default (classical AI is easy to skip wrongly).
- [ ] Copy that skipping T0 is allowed; lying to yourself is the failure mode.

### Rank 10 — E10 Contributions

**Outcome:** Outlines and harvest updates arrive as PRs with the Do-rail human gate.  
**Questions:** Q44, Q49.

Tasks:

- [ ] CONTRIBUTING + DCO or CLA decision.
- [ ] PR template: scorecard, sitting, rail (Do vs Skim).
- [ ] CODEOWNERS on `scripts/graph_spec.py` and `scripts/outlines.py`.
- [ ] Reject drive-by “add my course” to Do without ranking evidence.

### Rank 11 — E11 Map quality evals

**Outcome:** We know whether beginners finish T0, not only whether validate.py is green.  
**Questions:** Q50–Q54.

Tasks:

- [ ] Local, opt-in log: Focus opens, marks done, time-to-first-done (no PII).
- [ ] SLO: Do-rail link-check 100% on nightly.
- [ ] Quarterly: which stations stall (primary Do not done after 14 days of “doing”).
- [ ] Do not build a cloud analytics pipeline until E8 decision.

### Rank 12 — E12 Identity and sync (later)

**Outcome:** Multi-device progress without turning the atlas into an app platform.  
**Questions:** Q55–Q58. **Do not start** until E8 is chosen.

Tasks:

- [ ] Explicit non-goal until a second machine is a real pain.
- [ ] If ever: file-sync of `progress.json` (iCloud/Syncthing) before accounts.

---

## Distributable checklist (36 ship-gates)

A repo is **distributable** when a second engineer can install it, understand the ranking, keep progress, and we are not shipping legal or security debt. Not when it has a landing page.

| # | Gate | Epic | Done when |
|---|---|---|---|
| D01 | SPDX license on code | E3 | LICENSE file |
| D02 | Harvest attribution | E3 | ATTRIBUTION.md |
| D03 | Catalog vs code license split explained | E3 | README paragraph |
| D04 | Nominative use of course brands | E3 | PO note |
| D05 | Bind 127.0.0.1 + test | E3 | serve.py + unittest |
| D06 | PUT not exposed on LAN by default | E3 | documented |
| D07 | No secrets / .env in git | E3 | gitignore + scan |
| D08 | Deny-list for junk harvest URLs | E3 | compile already partial |
| D09 | Python version pin | E4 | README |
| D10 | Zero-dep serve path | E4 | `make serve` |
| D11 | LaunchAgent optional, not required | E4 | README |
| D12 | Port conflict recovery | E4 | error text |
| D13 | Non-macOS smoke | E4 | Linux or Docker note |
| D14 | First-run screenshot | E4 | docs or README |
| D15 | Git SHA / compile time in UI | E2, E4 | kicker or footer |
| D16 | CONTRIBUTING | E4, E10 | file |
| D17 | Issue templates | E4 | dead link, ranking |
| D18 | Progress schema version | E5 | progress.json |
| D19 | Backup/export progress | E5 | make target |
| D20 | Compile does not wipe progress | E5 | test |
| D21 | Deterministic resource ids | E5 | already hash(url) — document |
| D22 | Dead-link CI on Do rail | E2 | `make links` |
| D23 | Harvest pin + diff | E2 | hashes |
| D24 | Do-rail human gate | E2 | PR checklist |
| D25 | Changelog of catalog | E2 | CATALOG.md or Releases |
| D26 | Stale featured badge | E2 | 90-day rule |
| D27 | Scorecard visible on Do | E6 | UI line |
| D28 | “Skim is not homework” in install README | E4 | copy |
| D29 | Privacy: no telemetry default | E8, E11 | README |
| D30 | Distribution mode chosen (clone vs static) | E8 | ADR |
| D31 | If static: localStorage, no public PUT | E8 | impl |
| D32 | Accessibility of Focus + status | E7 | keyboard + names |
| D33 | Lesson outlines for T0–T1 primaries | E1 | parts in JSON |
| D34 | Covered-by child URLs | E1 | UI |
| D35 | Code of conduct if public | E10 | only if E8=public |
| D36 | “What this is not” | E3, E4 | README |

**Minimum set to share a zip with a friend:** D05–D07, D09–D11, D18–D20, D22, D28, D36, plus Focus working (E1 at least atomic, outlines nicer).  
**Minimum set to make the GitHub remote public:** all of D01–D08, D22–D25, D29–D30, D35.

---

## Catalog flywheel (how it stays alive)

The catalog dies in three ways: **link rot**, **stack age** (TensorFlow-era Do items), **silent harvest growth** that buries Do under 2,000 Skim rows.

### Operating cadence

| Cadence | Who | What | Human gate |
|---|---|---|---|
| Nightly | CI | `make links` on Do + Focus + featured | Fail the build; do not auto-delete |
| Weekly | Maintainer (30 min) | `make harvest-diff` vs pinned hashes; skim new URLs into Skim only | Yes before any Do change |
| Monthly | Maintainer (2 h) | Re-open T0–T3 Do winners against the scorecard; bump `sitting` if a course added a week | Yes |
| Quarterly | PM + engineer | Branch coverage (agents, evals, new paper types); add a station only with Do/Parallel/Skim/Project all nonempty | Yes |
| On news | Ad hoc | Frontier papers (new architecture) go to the matching T7/T3 station **Skim first**, Do only after a ranking pass | Yes |

### Rules

1. **Harvest is a library intake.** Awesome-lists may add hundreds of URLs. They never auto-promote to Do.
2. **Do is a product decision.** Changing `graph_spec.py` stations requires the scorecard evidence line.
3. **Pins over live scrapes.** Store the date and hash of each harvest file. Refetch is explicit.
4. **Featured link-rot is a bug.** Skim 404s are logged, not blocking, until a quarterly sweep.
5. **Stack age is a ranking input.** A 2017 TF course can stay on Skim; it should not remain a Do winner without a note.
6. **New fields must survive compile.** `sitting`, `parts`, `scores` live on curated rows so harvest upsert cannot blank them (already a compile risk — test it).
7. **Changelog is the user-facing freshness.** “Compiled Sep 2026 · 1,242 URLs · last Do-rail review {date}.”
8. **No cookieed properties.** Coursera/Pluralsight remain public listing URLs. Outlines for those are slug-only.

### Instrumentation (still local)

- `compiled_at`, `do_link_ok_ratio`, `featured_stale_count` in a small `data/catalog_meta.json`.
- Validate.py: ≥500 URLs, no empty rails, required branches, **and** every T0–T1 `do[0]` has `sitting`.

---

## Fifty-eight questions PM and PO must answer

Answer in writing on the epic (one paragraph). “TBD” is not an answer. Recommended default in parentheses where we already locked the product.

### Audience and job-to-be-done

1. Who is the primary user in year 1 — you, a hired learner, or a public beginner? (you, then one friend)
2. Is the job “become an SME in 2–3 years” or “never freeze on what to open tonight”? (both; Focus optimizes the second)
3. Do we serve people who cannot use Coursera/Pluralsight as first-class, or is employer access assumed after T0? (T0 theory stays free)
4. Is a complete ML beginner the only persona, or also a backend engineer skipping T0? (E9)
5. Are we willing to tell someone *not* to start agents this month? (yes — T3 after T2)
6. What does “done with the atlas” mean for a human career, if anything? (not 1,242; year-1 T0–T5 primaries)

### Pedagogy and scope

7. Is classical AI (search, logic, games, KG) mandatory in year 1 or a branch? (on the map in T1; Focus still walks station order)
8. Must every station keep four rails forever? (yes for validate; UI may hide)
9. Can a user mark “already know this” without doing the Do resource? (E9)
10. If they skip 3Blue1Brown, do we still show Imperial as Also, or skip the whole LA pair? (skip primary only)
11. Are projects (Build) required for Focus, or optional forever? (optional; Focus ignores Build)
12. What is a sitting — 45 min, 3 h, or “until the video series ends”? (~2–4 h as labeled)
13. Do slug-only Coursera weeks count as real progress or theater? (real ticks; Open still hits the parent)

### Ranking

14. Who is allowed to change a Do winner? (maintainer + scorecard evidence)
15. Do we publish numeric scores or only the ranked order? (order + one-line why; numbers optional)
16. How often do we re-rank T0–T2? (quarterly)
17. What happens when a new course beats a Do winner — move old to Parallel or Skim? (Parallel if same pedagogy, Skim if dated)
18. Is “modern stack” PyTorch-or-bust, or is a great TF course allowed on Parallel? (Parallel)

### Catalog

19. What is the catalog KPI — unique URLs, featured count, or Do-rail freshness? (freshness of Do + floor 500)
20. Cap on catalog size? (no cap; UI must not treat size as homework)
21. May we drop harvest files that go stale upstream? (yes, with changelog)
22. Do we accept user-submitted URLs into Skim without ranking? (Skim yes, Do no)
23. How do we treat paywalled papers? (abs page URL, not PDF scrape)
24. How do we treat YouTube mirrors of a university course already on Do? (containment / mirror, not a second Do)
25. What is the SLA to fix a 404 on a Focus URL? (7 days, P0)
26. Who owns arXiv intake for T7 branches? (maintainer; Skim-first)

### Progress and data

27. Is progress a git artifact, a browser artifact, or both? (git file now; E8 may add localStorage)
28. If parent is marked done, may the user still un-tick one lesson? (yes; parent becomes doing)
29. Do we ever auto-complete substitutes (Ng vs StatQuest)? (no in v1)
30. What if compile changes a resource id? (ids are url hashes — never change URL normalization lightly)

### Distribution and packaging

31. Is the first external surface a private git remote, public GitHub, or a zip? (private git until E3)
32. Do we support Windows? (not in E4; document WSL)
33. Do we want a hosted demo with fake progress? (no, until privacy review)
34. Is LaunchAgent a feature or a footgun for distribution? (optional extra)
35. What is the supported online mode — none, static, or server? (none, then static)
36. Do we need an installer (Homebrew, pip)? (no until 10+ users)

### Legal, ethics, security

37. Can we redistribute harvest markdown that is itself MIT/CC? (keep copies with attribution, or submodule)
38. Can we list Coursera URLs we do not own? (yes, links; no scraped videos)
39. Do lecture notes we did not write belong in the repo as files? (no; link out)
40. What is the policy on torrent / libgen links if they appear in awesome-lists? (deny-list)
41. GDPR/CCPA if we ever log Focus events? (E11 opt-in, local-only first)
42. Are we comfortable with a public PUT endpoint ever? (no)

### Community, metrics, risk

43. If public, do we take sponsorships or affiliate Coursera links? (default no)
44. Who reviews ranking PRs? (you + CODEOWNERS)
45. What is the kill criterion for a harvest source (too much junk)? (deny-list ratio, maintainer judgment)
46. Do we let users fork the station graph (custom T0)? (not v1; data is the product)
47. Is mobile a goal or best-effort? (best-effort laptop in E7)
48. What is the disclosure if a ranking is our opinion, not a standard? (README: opinionated scorecard)
49. Contributor license for outlines? (same as code license unless legal says CLA)
50. North-star metric? (time-to-first-Focus-done; T0 primary completion in 14 days)
51. Counter-metric so we do not gamify ticks? (do not celebrate 1,242; celebrate sittings on Do)
52. How do we detect the map is wrong (users skip T1 eval)? (E11 stall report)
53. What is the rollback if a Do swap is bad? (git revert graph_spec; changelog)
54. How much maintainer time per month is committed? (must answer; flywheel dies below ~3 h)
55. Multi-user in one browser? (no)
56. Teams / cohorts? (no until E12)
57. Offline / air-gapped install? (possible: freeze JSON; not a goal)
58. When do we stop calling it a private atlas and start calling it a product with users? (after D-minimum zip + one friend finished T0 primary)

---

## How to groom

1. Answer the questions clustered on the next epic (not all 58 at once).
2. Copy that epic’s task list into the tracker; do not add stories that skip the human gate on Do-rail.
3. Immediate-needs list is the sprint. Epics 1–4 are the quarter. Epics 8–12 wait on answers to Q31 and Q54.

Full interactive board: open the Cursor canvas `atlas-product-backlog.canvas.tsx` beside chat.
