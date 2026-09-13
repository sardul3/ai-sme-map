# Next lesson + containment — Design

Date: 2026-09-12
Status: draft (picker + duplicate forks locked in chat)

## Goal

A beginner opening the atlas always sees **one next lesson** they can finish in a sitting, can tick each lesson, and is not sent to a child URL that is already inside a finished parent listing.

## Locked decisions

- **Next** = first unfinished part of the current station’s **first Do item**. When that item is complete, Focus moves to the **next station**, even if later Do items (ISL beside Ng, Imperial beside 3Blue1Brown) are still todo.
- **Duplicate** = **containment only**: lessons/chapters/mirrors under one listing. Not “same topic” substitutes (Ng does not auto-cover StatQuest).
- Do **not** explode the harvest catalog into YouTube videos.

## Non-goals

- Pedagogical substitutes / `covers` across different courses.
- Scraping Coursera, YouTube Data API, or employer cookies.
- Changing station rails, ranking, or the 500-URL floor.
- Requiring every catalog row to have parts.

## Why this is the right size

Today `progress.json` is `{resourceId: todo|doing|skimmed|done}` and `nextStation` requires **every** Do URL on a station. That is a 20–40 hour unit. Child URLs already in the catalog (`course.fast.ai` vs `Lessons/lesson1.html`) are unrelated rows.

Shared IDs already credit the **same URL** on two stations. This feature is for **nested URLs and week-level checklists**, not for that case.

## Data

### Parts live on the parent resource

After compile, a Do course/lecture-series may have:

```json
"parts": [
  {"id": "r-abc:vectors", "title": "Vectors", "url": "https://3blue1brown.com/lessons/vectors"},
  {"id": "r-xyz:week-1", "title": "Week 1 — supervised learning", "url": null}
]
```

- `id` is stable (`parent_id + ":" + slug`). It is a progress key, not necessarily a catalog URL.
- `url` is optional. Use a real unique http(s) URL when the lesson is a public page. Use `null` for Coursera weeks and other login walls.
- If `url` is set, compile **upserts** a catalog row: `kind: "lesson"`, `parent_id`, `featured: false`. Search can find it. Unique-URL rule still holds.
- Source of outlines: `scripts/outlines.py` (`OUTLINES` keyed by **normalized parent URL**). Not inferred from harvest headings.

### Progress

Still a flat map in `data/progress.json`:

```json
{
  "r-parent": "doing",
  "r-parent:vectors": "done"
}
```

Allowed values unchanged: `todo` | `doing` | `skimmed` | `done`. Missing key = `todo`.

### Containment / rollup (write path)

When the user sets a status:

| Action | Effect |
|---|---|
| Parent → `done` | All parts → `done` |
| Parent → `todo` / `doing` / `skimmed` | Parts unchanged (do not wipe lesson ticks) |
| Last part → `done` | Parent → `done` |
| Any part → not `done` | Parent cannot stay `done` (set parent to `doing`) |

Picker **read path** (even if the user never rolled up): a parent is complete if it is `done` **or** every part is `done`. A part is complete if it is `done` **or** its parent is `done`.

No URL-prefix auto-attach. A harvest row becomes a child only if its URL is listed in that parent’s outline.

## Focus picker

`primary = station.do[0]`. Stations stay in `graph.nodes` order.

```
for station in nodes:
    primary = station.do[0]
    if primary has parts:
        for part in parts:
            if part not complete: return station, primary, part
        if primary not complete: return station, primary, None
        continue
    if primary not complete: return station, primary, None
return atlas complete
```

Papers, articles, books without outlines stay one checkbox. Completing that checkbox moves Focus to the next station.

The map’s `nDone/nDo` still counts **all** Do items. Later Do items remain visible in the drawer. They are optional relative to Focus.

## UI

- Header **Next** shows the lesson title (or the atomic resource title), not only the station.
- A Focus strip: parent · lesson · station, Open, Mark done.
- Drawer: a Do parent with parts renders an ordered lesson list; each row has the same status buttons.
- A catalog/search hit that is a lesson shows `lesson of {parent}`. If the parent is complete, show **covered by {parent}** and do not offer it as Focus.
- No new visual language beyond the existing timetable (orange theory / cerulean practice).

## Server

Python owns the algorithm (`scripts/focus.py`) so it can be unit-tested without a browser.

- `GET /data/focus.json` → current Focus object (or `{done: true}`).
- `PUT /data/progress.json` runs rollup against compiled resources, writes the file, returns `{progress, focus}` (200). Existing clients that ignore the body still persist.

Restart the LaunchAgent after `serve.py` changes so port 7432 picks up the handler.

## Outlines to ship in the first implementation

Engine must work with **zero** outlines (atomic primary Do). Seed public TOCs that have stable URLs, then slug-only weeks:

1. 3Blue1Brown Essence of Linear Algebra (lesson pages).
2. fast.ai Practical Deep Learning (existing `Lessons/lessonN.html` where live).
3. Neural Networks: Zero to Hero (known lecture URLs).
4. Ng Machine Learning Specialization (slug-only weeks; url null).
5. Imperial MML Linear Algebra (slug-only weeks; url null).

Further T0–T2 Do courses are content follow-ups, not blockers.

## Success

- `python3 -m unittest discover -s tests` passes.
- `make validate` still passes (≥500 unique http URLs; lessons with URLs count; slug-only parts do not need catalog rows).
- Reload of http://127.0.0.1:7432 shows a Focus lesson; marking it done advances Focus; marking the parent done covers remaining parts; a child URL in search shows covered-by when the parent is done.
- Completing 3Blue1Brown does **not** mark Imperial done.

## Testing

Pure functions in `scripts/focus.py`: `is_complete`, `apply_status`, `next_focus`. Fixtures are tiny in-memory graph/resource lists, not the full catalog.
