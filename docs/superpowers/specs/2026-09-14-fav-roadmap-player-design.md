# Pins, Roadmap canvas, Mini-player — Design

Date: 2026-09-14
Status: approved in chat (architecture A; pin Focus; every-URL canvas; git overlay; mini follows)

## Goal

Three learner/author surfaces on the existing localhost + GitHub Pages atlas:

1. **Pin** a course listing so it becomes that station’s personal start-here (Focus follows the pin).
2. **Roadmap** — a pan/zoom graph of every harvested URL, grouped under checkpoints (stations) and harvest-file clusters, with localhost drag that writes the git catalog overlay.
3. **Player** — no chrome on Tonight until the user hits Play; then a minimizable mini-player follows Tonight / Commute / Library / Roadmap until dismissed.

## Locked decisions

- Approach A: new `roadmap.html` page. Tonight keeps Focus and the dual-rail timetable.
- Pin = personal overlay in progress. One pin per station. Does not rewrite git ranking.
- Every harvested URL is a graph node. Assigned nodes live inside checkpoints; unassigned nodes are all visible, clustered by harvest file.
- Author places checkpoints (and harvest clusters). Resource nodes auto-flow inside the group in four lanes: MUST / ELECTIVE / MAY / Build.
- MUST = `do`, ELECTIVE = `parallel`, MAY = `skim`, Build = `project`.
- Drag-assign writes git files via localhost PUT. GitHub Pages is view + pins + player only.
- v1 editor: move a resource between checkpoints and lanes, drop unassigned onto a checkpoint, return a resource to Library. No create/rename/delete checkpoints.
- After Play: mini chrome on Tonight, Library, and Roadmap; full deck on Commute. Minimize/expand is a toggle. Dismiss clears playback.

## Non-goals

- Accounts, hosted PUT, or binding `0.0.0.0`.
- Official roadmap.sh export or import.
- Creating or deleting stations in the editor.
- Per-resource free-form `{x,y}`.
- npm / third-party JS. Python stays stdlib-only.
- Replacing Tonight’s dual-rail timetable.
- Pins that jump Focus to a later stage while earlier stations are unfinished.
- Auto-playing audio on Tonight before the user hits Play.

## Why this is the right size

The catalog already has 61 stations with prereqs (`graph.json`) and ~1,200 URLs. Tonight is a sitting UI, not a map of the whole harvest. Pins are a personal “do this first” without forking `graph_spec.py`. Assignments are the human Do-rail edit the flywheel already requires, stored as JSON instead of Python surgery. The player markup already exists on Tonight and Commute and must stop being a deck on a page where nobody asked for audio.

---

## 1. Pins (favorites)

### Storage

`data/progress.json` (localhost PUT, existing handler) and `localStorage.atlas_progress` (Pages) gain a reserved object key:

```json
{
  "schema_version": 1,
  "pins": { "s-la-see": "r-340c2f1719" },
  "r-340c2f1719": "doing"
}
```

`pins` is not a resource id. Rollup, status buttons, and sitting counts ignore it. Missing `pins` equals `{}`.

### Semantics

- One pin per station. Starring another course on the same station replaces the pin. Starring the pinned course again clears that station’s pin.
- Star in a station drawer pins to **that** station, even if the resource is not on its rails.
- Star from Library or search pins to the station currently open in the drawer; if none is open, to the current Focus station.
- Pin does not write `assignments.json`. Drop-to-MUST is the catalog move; the star is “tonight I want this.”

### Focus (`scripts/focus.py` and `web/app.js`, keep in sync)

Stations still walk in `graph.nodes` order. For each station:

```
primary_id = pins[station.id] if that id exists in the catalog and is not complete
             else station.do[0]
if primary is missing, continue
if primary has parts: first unfinished part, else the parent if still incomplete
if primary is incomplete: return Focus on that primary
```

Completing a pin does **not** skip the compiled winner. The pin is then treated as missing and Focus falls back to `do[0]` on the same station. Unstar has the same effect. The existing skip control still marks the compiled primary done.

Pins never skip stations: a pin on a T4 station is ignored until every earlier station’s current primary (pin or `do[0]`) is complete.

### Listing order

In a station drawer, Do (MUST) lists the pinned resource first with the start-here badge when the pin is set and not complete, then the compiled `do` ids (the pinned id is not duplicated). Parallel / Skim / Build order is unchanged. Search hits show a filled star when that resource is the pin for any station.

### UI

Star control on each resource card (`aria-label="Pin as start here"` / `"Unpin start here"`). Filled when this resource is that station’s pin (drawer) or any pin (search/library).

---

## 2. Roadmap canvas

### Navigation

Mast nav on all pages: Tonight · Commute · Library · Roadmap.

| File | Role |
|---|---|
| `web/roadmap.html` | Canvas page (`data-page="roadmap"`) |
| `data/assignments.json` | Catalog overlay: where a resource sits |
| `data/roadmap_layout.json` | `{x,y}` for checkpoints and harvest clusters |
| `scripts/assignments.py` | Merge overlay onto station rails; classify unassigned |
| `scripts/atlas_paths.py` | Add `roadmap` to `PAGE_STEMS` |

### Assignments overlay

```json
{
  "schema_version": 1,
  "placements": {
    "r-abc": { "station": "s-la-see", "rail": "parallel" },
    "r-def": null
  }
}
```

`rail` is one of `do` | `parallel` | `skim` | `project`.

Compile merge, per resource id:

| `placements[id]` | Effect |
|---|---|
| missing | Keep seed rails from `graph_spec.py` |
| `null` | Strip from every station rail (Library / harvest cluster) |
| `{station, rail}` | Strip from every rail, then append to that station’s rail |

Unknown resource id or unknown station id: skip that entry, do not fail compile. Catalog floor ≥500 unique URLs still applies.

Seed `graph_spec.py` URL lists remain the default map. `assignments.json` is the file the author commits after a canvas session. CI must not invent placements. Weekly onboard still must not edit Do rails; it also must not write `assignments.json`.

Return to Library: if that resource id still appears in seed `graph_spec.py` rails, write `placements[id] = null`. Otherwise delete the key. Never leave a placement that compile would put back on a station.

### Layout overlay

```json
{
  "schema_version": 1,
  "checkpoints": { "s-la-see": { "x": 48, "y": 96 } },
  "clusters": { "awesome-ml.md": { "x": 920, "y": 48 } }
}
```

Missing keys get a deterministic default: stages left-to-right (T0…T7), theory above practice inside a stage, harvest clusters in a column to the right of T7. Defaults are computed in JS when layout is absent; dragging persists the moved group only.

### Canvas

Vanilla SVG. Shared pins, player, drawer, and progress stay in `web/app.js`. Canvas layout and drag live in `web/roadmap.js`, loaded only by `roadmap.html`. No new packages.

- Pan (drag background), zoom (wheel), fit-to-view control.
- Checkpoint group: title, stage, theory/practice rail color, four labeled lanes MUST / ELECTIVE / MAY / Build. Resource nodes auto-flow as rects + truncated title + done check + star.
- Edges: station `prereqs` only (checkpoint to checkpoint), not URL-to-URL.
- Unassigned: one group per harvest `source` filename (and `curated` / other library categories already used by `scripts/library.py`). All nodes in those groups are painted; they are not collapsed in v1.
- Click a resource node: same drawer as Tonight (station context if assigned; library-style card if not).
- Commute episodes (`audio_url` + `purpose`) stay off this canvas. Eyes-off remains `commute.html`.

~1,200 simple rects. No force-directed layout. Zoom in to read labels.

### Authoring

Enabled only when `location.hostname` is `127.0.0.1`, `localhost`, or `::1`.

- Drag resource → another lane or checkpoint: PUT `assignments.json` with that placement. The handler writes the file, merges placements into `data/graph.json` station rails (same function as compile; does not re-harvest), and returns the merged graph. The client re-renders from that payload. `make compile` applies the same merge so a later rebuild cannot clobber the overlay.
- Drag resource → a harvest cluster, or an explicit “Library” control: tombstone or delete as specified above.
- Drag checkpoint or harvest cluster: PUT `roadmap_layout.json` only.

On GitHub Pages, pointer drag is disabled. Dropping is not silently ignored: if a drag is attempted, the node snaps back and a one-line note says assignments are localhost-only.

### Serve and export

- `PUT /data/assignments.json` and `PUT /data/roadmap_layout.json`: same loopback-only 403 as progress. Body must be a JSON object. Validate `placements` values are `null` or `{station: string, rail: one of four}`.
- After a valid assignments PUT, run the merge into `data/graph.json` so Tonight and Roadmap agree without requiring a separate `make compile` in that session. `make compile` must apply the same merge so git stays coherent.
- `GET /roadmap` and `/roadmap.html` → `web/roadmap.html`.
- `export_static` copies `roadmap.html`, `assignments.json`, and `roadmap_layout.json`. Public `progress.json` stays `{schema_version: 1}` (no pins).

---

## 3. Mini-player

### Visibility

All four pages may include the existing player markup. It stays `hidden` until `sessionStorage.atlas_now_playing` holds a known resource id with `audio_url`.

Tonight (`index.html`) must not show chrome, and must not start audio, on a cold load.

### Session

```js
// sessionStorage.atlas_now_playing
{ "id": "r-…", "playing": true }

// localStorage.atlas_player_size  →  "mini" | "deck"
// localStorage.atlas_commute_pos  →  unchanged (per-id time + speed)
```

Play writes `atlas_now_playing` and unhides chrome. Navigating among Tonight / Commute / Library / Roadmap restores src, time, and chrome. If `playing` is true, call `play()`; if the browser blocks autoplay, chrome stays visible and paused.

Default size after Play: **mini** on Tonight, Library, Roadmap; **deck** on Commute. User toggle is stored in `atlas_player_size` and wins over the default for the rest of the session.

### Chrome

- **Deck** — current commute player (prev/next, ±15s, scrubber, speed).
- **Mini** — sticky bottom-right: purpose mark, truncated title, play/pause, expand, dismiss (X). Audio continues while minimized.
- **Dismiss** — pause, clear `src`, remove `atlas_now_playing`, hide chrome on this page. Pause without dismiss keeps chrome.
- Space play/pauses only when chrome is visible.

Audio error (`error` event or rejected `play()`): chrome stays up, control shows Play, position is not wiped.

Private mode without `sessionStorage`: player works on the current page only; it does not follow navigation.

---

## Error handling

| Case | Behavior |
|---|---|
| Pages PUT / drag-assign | Snap back; note “assignments are localhost-only” |
| PUT 400/403 | Snap back; do not write `graph.json` |
| Stale assignment id | Compile skips; validate still passes if URL floor holds |
| Pin to unknown id | Focus ignores pin, uses `do[0]` |
| Layout missing a checkpoint | Default grid position |
| `sessionStorage` unavailable | In-memory player on this page only |

---

## Testing

Python unittest only (existing style). Extract pin + merge logic in `scripts/focus.py` and `scripts/assignments.py`.

- Pin set → `next_focus` returns that resource (and first unfinished part).
- Pin done or unknown → fallback to `do[0]`.
- Pin on a later station while an earlier primary is open → Focus stays on the earlier station.
- Merge: placement moves a harvest id onto `parallel`; tombstone strips a seed Do id; missing key leaves seed.
- `unassigned()` treats overlay placements as assigned and tombstones as unassigned.
- Serve: PUT assignments/layout 403 off loopback; GET `/roadmap` is 200.
- `atlas_root("/roadmap.html")` is site root. Static HTML for `roadmap.html` uses relative `styles.css` / `app.js`.
- Export includes `roadmap.html` and the two overlay JSON files; exported progress has no pins.
- Homepage HTML: `#player` has the `hidden` attribute in the shipped markup (cold load). Commute unchanged.

Player follow-across-pages is verified in the browser after implementation (Play on Commute, open Tonight, mini visible, dismiss hides it). No new JS test runner.

## Success

- Starring a Parallel course on the current station makes it Tonight until it is done or unstarred.
- Opening Roadmap shows checkpoints and harvest clusters with resource nodes; localhost drag of a Library node onto MUST updates `assignments.json` and Tonight’s drawer after reload; Pages cannot persist that drag.
- Cold Tonight has no player. After Play on Commute, Tonight shows a mini-player that can expand, minimize, and dismiss.

## Rollback

Revert the feature branch. Overlay files are additive; deleting `assignments.json` / `roadmap_layout.json` restores seed `graph_spec.py` rails and default positions. Pins in existing `progress.json` are ignored by old code if the key is never read.
