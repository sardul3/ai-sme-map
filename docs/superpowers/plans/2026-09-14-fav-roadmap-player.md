# Pins, Roadmap canvas, Mini-player Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Personal pins become a station’s start-here (Focus follows them); a pan/zoom Roadmap page shows every harvested URL under checkpoints and harvest clusters with localhost drag writing `assignments.json`; Tonight shows no audio chrome until Play, then a mini-player follows across pages until dismissed.

**Architecture:** Pins live in `progress.pins` and change `next_focus` only. Catalog moves live in `data/assignments.json`, merged onto station rails at compile and on localhost PUT. Layout lives in `data/roadmap_layout.json`. Shared UI stays in `web/app.js`; canvas + drag live in `web/roadmap.js`. Zero new packages.

**Tech Stack:** Python 3.12 stdlib, vanilla JS modules, SVG, existing unittest suite, loopback `scripts/serve.py`.

## Global Constraints

- Python 3.12+, zero third-party packages. No npm.
- PUT only on loopback; GitHub Pages is static (`localStorage` / `sessionStorage`).
- `nextFocus` in `web/app.js` stays in sync with `scripts/focus.py`.
- MUST / ELECTIVE / MAY / Build are labels for `do` / `parallel` / `skim` / `project`.
- Weekly onboard must not write `assignments.json` or `graph_spec.py`.
- Do not bind `0.0.0.0`. Do not add accounts.
- Spec: `docs/superpowers/specs/2026-09-14-fav-roadmap-player-design.md`.

### Files (locked)

| File | Responsibility |
|---|---|
| `scripts/focus.py` | `pins_of`, `station_primary`, `do_ids_for_station`, `next_focus` |
| `scripts/assignments.py` | Load/validate/merge placements; default empty overlay |
| `scripts/compile_catalog.py` | Call merge after resolving seed rails |
| `scripts/serve.py` | Roadmap GET; PUT assignments + layout; merge graph on assignments PUT |
| `scripts/atlas_paths.py` | `roadmap` page stem |
| `scripts/export_static.py` | Copy `roadmap.html`, `roadmap.js`, overlay JSON |
| `scripts/library.py` | Unassigned uses merged graph (no change if merge is in graph.json) |
| `web/app.js` | Pin UI, player session, nav-agnostic player restore |
| `web/roadmap.js` | SVG canvas, pan/zoom, drag (localhost) |
| `web/roadmap.html` | Roadmap page |
| `web/index.html`, `web/commute.html`, `web/library.html` | Nav + player chrome |
| `web/styles.css` | Star, mini-player, canvas |
| `data/assignments.json` | `{schema_version, placements}` |
| `data/roadmap_layout.json` | `{schema_version, checkpoints, clusters}` |
| `tests/test_focus.py` | Pin Focus cases |
| `tests/test_assignments.py` | Merge / tombstone |
| `tests/test_static_pages.py`, `tests/test_library.py` | Nav, export, player hidden |

---

### Task 1: Pin-aware Focus (Python)

**Files:**
- Modify: `scripts/focus.py`
- Test: `tests/test_focus.py`

**Interfaces:**
- Consumes: existing `next_focus(graph, resources, progress)`, `is_complete`
- Produces: `pins_of(progress) -> dict[str, str]`, `station_primary(station, progress, resources_by_id) -> str | None`, `do_ids_for_station(station, progress, resources_by_id) -> list[str]`, `next_focus` uses pin then `do[0]`

- [ ] **Step 1: Write the failing tests**

Add `r-extra` to `RES` in `tests/test_focus.py` and a `TestPins` class:

```python
RES.append({"id": "r-extra", "title": "Pinned extra", "url": "https://example.com/extra-course", "sitting": "~1 h"})


class TestPins(unittest.TestCase):
    def test_given_pin_when_focus_then_pinned_resource(self):
        f = next_focus(GRAPH, RES, {"pins": {"s-a": "r-extra"}})
        self.assertEqual(f["station_id"], "s-a")
        self.assertEqual(f["resource_id"], "r-extra")
        self.assertIsNone(f["part_id"])

    def test_given_pin_done_when_focus_then_compiled_do0(self):
        f = next_focus(GRAPH, RES, {"pins": {"s-a": "r-extra"}, "r-extra": "done"})
        self.assertEqual(f["resource_id"], "r-3b1b")
        self.assertEqual(f["part_id"], "r-3b1b:vectors")

    def test_given_unknown_pin_when_focus_then_compiled_do0(self):
        f = next_focus(GRAPH, RES, {"pins": {"s-a": "r-missing"}})
        self.assertEqual(f["resource_id"], "r-3b1b")

    def test_given_later_station_pin_when_earlier_open_then_stay(self):
        f = next_focus(GRAPH, RES, {"pins": {"s-c": "r-extra"}})
        self.assertEqual(f["station_id"], "s-a")
        self.assertEqual(f["resource_id"], "r-3b1b")

    def test_given_pin_with_parts_when_focus_then_first_part(self):
        f = next_focus(GRAPH, RES, {"pins": {"s-b": "r-imperial"}, "r-3b1b": "done"})
        self.assertEqual(f["station_id"], "s-b")
        self.assertEqual(f["resource_id"], "r-imperial")
        self.assertEqual(f["part_id"], "r-imperial:week-1")

    def test_do_ids_put_pin_first_without_duplicate(self):
        from focus import do_ids_for_station, by_id

        ids = do_ids_for_station(GRAPH["nodes"][0], {"pins": {"s-a": "r-extra"}}, by_id(RES))
        self.assertEqual(ids[0], "r-extra")
        self.assertEqual(ids[1], "r-3b1b")
        self.assertEqual(len(ids), 2)
```

Also change `from focus import apply_status, is_complete, next_focus, rollup_all` to include `do_ids_for_station`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_focus.TestPins -v`

Expected: FAIL with `ImportError` or `AssertionError` (`do_ids_for_station` missing / Focus still `r-3b1b`).

- [ ] **Step 3: Write minimal implementation**

In `scripts/focus.py`, add helpers and change `next_focus` to use `station_primary`. Keep `_focus` / `apply_status` / `is_complete` unchanged. Preserve the `pins` key through `apply_status` (it already copies the dict).

```python
def pins_of(progress: dict) -> dict[str, str]:
    raw = progress.get("pins")
    if not isinstance(raw, dict):
        return {}
    return {k: v for k, v in raw.items() if isinstance(k, str) and isinstance(v, str)}


def station_primary(station: dict, progress: dict, resources_by_id: dict) -> str | None:
    pin = pins_of(progress).get(station["id"])
    if pin and pin in resources_by_id and not is_complete(progress, pin, resources_by_id):
        return pin
    do = station.get("do") or []
    return do[0] if do else None


def do_ids_for_station(station: dict, progress: dict, resources_by_id: dict) -> list[str]:
    do = list(station.get("do") or [])
    pin = pins_of(progress).get(station["id"])
    if pin and pin in resources_by_id and not is_complete(progress, pin, resources_by_id):
        return [pin] + [i for i in do if i != pin]
    return do
```

Replace the `do[0]` lookup in `next_focus` with:

```python
        primary_id = station_primary(station, progress, resources_by_id)
        if not primary_id:
            continue
        rec = resources_by_id.get(primary_id)
        if not rec:
            continue
```

If a station has empty `do` but a live pin, `station_primary` still returns the pin — do not `continue` on empty `do` before calling `station_primary`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_focus -v`

Expected: PASS (existing tests plus `TestPins`).

- [ ] **Step 5: Commit**

```bash
git add scripts/focus.py tests/test_focus.py
git commit -m "$(cat <<'EOF'
feat: honor per-station pins when picking Focus

EOF
)"
```

---

### Task 2: Pin star on listings (JS + HTML)

**Files:**
- Modify: `web/app.js`
- Modify: `web/styles.css`
- Test: `tests/test_library.py` (string contracts on `app.js`)

**Interfaces:**
- Consumes: `pins_of` / `do_ids_for_station` semantics from Task 1
- Produces: `nextFocus` matches Python; `togglePin(stationId, resourceId)`; star button `data-pin`; drawer Do list uses pin-first ids

- [ ] **Step 1: Write the failing test**

Append to `tests/test_library.py`:

```python
class TestPinUiContract(unittest.TestCase):
    def test_given_app_js_when_read_then_pin_helpers_and_star_control(self):
        js = (ROOT / "web" / "app.js").read_text()
        self.assertIn("function pinsOf", js)
        self.assertIn("function stationPrimary", js)
        self.assertIn("function doIdsForStation", js)
        self.assertIn("data-pin", js)
        self.assertIn('progress.pins', js)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_library.TestPinUiContract -v`

Expected: FAIL (`pinsOf` not found).

- [ ] **Step 3: Implement pin helpers and UI in `web/app.js`**

Keep in sync with `scripts/focus.py`. After `isComplete`:

```javascript
function pinsOf(progress) {
  const raw = progress && progress.pins;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return {};
  const out = {};
  for (const [k, v] of Object.entries(raw)) {
    if (typeof k === "string" && typeof v === "string") out[k] = v;
  }
  return out;
}

function stationPrimary(station, progress, byId) {
  const pin = pinsOf(progress)[station.id];
  if (pin && byId[pin] && !isComplete(progress, pin, byId)) return pin;
  return (station.do || [])[0] || null;
}

function doIdsForStation(station, progress, byId) {
  const doIds = [...(station.do || [])];
  const pin = pinsOf(progress)[station.id];
  if (pin && byId[pin] && !isComplete(progress, pin, byId)) {
    return [pin, ...doIds.filter((id) => id !== pin)];
  }
  return doIds;
}

function togglePin(progress, stationId, resourceId) {
  const pins = { ...pinsOf(progress) };
  if (pins[stationId] === resourceId) delete pins[stationId];
  else pins[stationId] = resourceId;
  return { ...progress, pins };
}

function pinStationForCard(explicitStationId) {
  if (explicitStationId) return explicitStationId;
  if (PAGE !== "commute" && active && active.id) return active.id;
  const focus = nextFocus(state.graph, state.resources, state.progress);
  return focus.done ? null : focus.stationId;
}
```

Change `nextFocus` to use `stationPrimary` instead of `doIds[0]`, including the empty-`do` case (skip only when `stationPrimary` is null).

In `renderResource`, add a star button. Signature becomes `renderResource(r, progress, { rank = 0, rail = "do", stationId = null } = {})`:

```javascript
function starButton(r, progress, stationId) {
  const sid = pinStationForCard(stationId);
  if (!sid) return "";
  const on = pinsOf(progress)[sid] === r.id;
  const label = on ? "Unpin start here" : "Pin as start here";
  return `<button type="button" class="star ${on ? "on" : ""}" data-pin="${r.id}" data-pin-station="${sid}" aria-pressed="${on}" aria-label="${label}">★</button>`;
}
```

Put `starButton` in `.status` next to existing buttons. Pass `stationId: node.id` from `rail()` / `renderDrawer`. For library/search cards, omit `stationId` so `pinStationForCard` uses the open station or Focus station.

In `rail()`, use `doIdsForStation` when `kind === "do"`:

```javascript
function rail(title, ids, byId, progress, kind, { open = true, station = null } = {}) {
  const list = kind === "do" && station ? doIdsForStation(station, progress, byId) : ids;
  // map list instead of ids; pass stationId: station && station.id
}
```

Call `rail("Do (ranked)", node.do, ..., "do", { station: node })`.

Click handler (with other `data-*` clicks):

```javascript
  const pinBtn = ev.target.closest("[data-pin]");
  if (pinBtn) {
    const sid = pinBtn.dataset.pinStation;
    const rid = pinBtn.dataset.pin;
    if (!sid || !rid) return;
    snapshot();
    state.progress = togglePin(state.progress, sid, rid);
    await persistAndRedraw();
    return;
  }
```

CSS (star is ink, filled when `.on` uses `--theory`):

```css
.status .star {
  font-size: 16px;
  line-height: 1;
  color: var(--muted);
  background: transparent;
  border: 1px solid var(--rule);
}
.status .star.on { color: var(--theory); border-color: var(--theory); }
```

- [ ] **Step 4: Run tests**

Run: `python3 -m unittest tests.test_library.TestPinUiContract tests.test_focus -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/app.js web/styles.css tests/test_library.py
git commit -m "$(cat <<'EOF'
feat: star a listing to pin it as station start-here

EOF
)"
```

---

### Task 3: Mini-player — hidden until Play, follows pages

**Files:**
- Modify: `web/index.html`, `web/commute.html`, `web/library.html`
- Modify: `web/app.js`, `web/styles.css`
- Test: `tests/test_static_pages.py` (or a new `tests/test_player_chrome.py`)

**Interfaces:**
- Consumes: existing `playCommute`, `COMMUTE_POS_KEY`
- Produces: `NOW_PLAYING_KEY = "atlas_now_playing"`, `PLAYER_SIZE_KEY = "atlas_player_size"`, `applyPlayerChrome()`, dismiss / size toggle

- [ ] **Step 1: Write the failing tests**

Create `tests/test_player_chrome.py`:

```python
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestPlayerChrome(unittest.TestCase):
    def test_given_homepage_when_read_then_player_is_hidden(self):
        html = (ROOT / "web" / "index.html").read_text()
        self.assertIn('id="player"', html)
        self.assertIn('id="player" hidden', html)
        self.assertIn('id="player-dismiss"', html)
        self.assertIn('id="player-size"', html)

    def test_given_library_when_read_then_player_shell_exists_hidden(self):
        html = (ROOT / "web" / "library.html").read_text()
        self.assertIn('id="player" hidden', html)
        self.assertIn('id="player-audio"', html)

    def test_given_app_js_when_read_then_session_now_playing(self):
        js = (ROOT / "web" / "app.js").read_text()
        self.assertIn("atlas_now_playing", js)
        self.assertIn("atlas_player_size", js)
        self.assertIn("player-dismiss", js)
        self.assertIn("player-mini", js)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_player_chrome -v`

Expected: FAIL (`player-dismiss` missing; library has no player).

- [ ] **Step 3: Implement chrome + session**

Copy the homepage player `<aside>` onto `library.html` (before `app.js`). Add two controls to **every** player (index, commute, library) inside `.player-copy` or a `.player-chrome` row:

```html
<div class="player-chrome">
  <button type="button" id="player-size" aria-label="Minimize player">Mini</button>
  <button type="button" id="player-dismiss" aria-label="Dismiss player">Dismiss</button>
</div>
```

Keep `id="player" hidden` on all of them.

In `web/app.js`:

```javascript
const NOW_PLAYING_KEY = "atlas_now_playing";
const PLAYER_SIZE_KEY = "atlas_player_size";

function readNowPlaying() {
  try {
    return JSON.parse(sessionStorage.getItem(NOW_PLAYING_KEY) || "null");
  } catch {
    return null;
  }
}

function writeNowPlaying(rec, playing) {
  try {
    if (!rec) {
      sessionStorage.removeItem(NOW_PLAYING_KEY);
      return;
    }
    sessionStorage.setItem(NOW_PLAYING_KEY, JSON.stringify({ id: rec.id, playing: !!playing }));
  } catch {
    /* private mode */
  }
}

function pagePlayerDefaultSize() {
  return PAGE === "commute" ? "deck" : "mini";
}

function playerSize() {
  try {
    const stored = localStorage.getItem(PLAYER_SIZE_KEY);
    if (stored === "mini" || stored === "deck") return stored;
  } catch {
    /* ignore */
  }
  return pagePlayerDefaultSize();
}

function applyPlayerChrome() {
  const box = $("player");
  if (!box) return;
  const size = playerSize();
  box.classList.toggle("player-mini", size === "mini");
  box.classList.toggle("player-deck", size !== "mini");
  const sizeBtn = $("player-size");
  if (sizeBtn) {
    sizeBtn.textContent = size === "mini" ? "Expand" : "Mini";
    sizeBtn.setAttribute("aria-label", size === "mini" ? "Expand player" : "Minimize player");
  }
}

function dismissPlayer() {
  const audio = $("player-audio");
  const box = $("player");
  if (audio) {
    audio.pause();
    audio.removeAttribute("src");
    audio.load();
  }
  state.nowPlaying = null;
  writeNowPlaying(null, false);
  if (box) box.hidden = true;
}
```

Change `playCommute(id)` to `playCommute(id, { autoplay = true } = {})`:
- After setting `state.nowPlaying` and `box.hidden = false`, call `writeNowPlaying(rec, autoplay)` and `applyPlayerChrome()`.
- Call `audio.play()` only when `autoplay` is true; otherwise restore `src` + time only.

On `audio.play` / `pause` events, `writeNowPlaying(state.nowPlaying, !audio.paused)`.

After `const state = await load();` and `bindPlayer();` (call `bindPlayer` even if hidden), restore:

```javascript
const pending = readNowPlaying();
if (pending && pending.id && state.byId[pending.id] && state.byId[pending.id].audio_url) {
  playCommute(pending.id, { autoplay: !!pending.playing });
}
```

Click handlers for `#player-size` (toggle `mini`/`deck` in `localStorage`, `applyPlayerChrome`) and `#player-dismiss` (`dismissPlayer`).

Space handler already checks `!$("player").hidden` — keep that.

CSS: `.player.player-mini` is `position: fixed; right: 16px; bottom: 16px; left: auto; width: min(22rem, calc(100vw - 32px)); grid-template-columns: auto 1fr auto; margin: 0;` Hide `.player-mini .player-seek-label`, `.player-mini .speeds`, `.player-mini [data-skip]`, `.player-mini #player-prev`, `.player-mini #player-next`. Keep title, play, size, dismiss.

Do **not** unhide the player in `redraw()`. Only `playCommute` / restore unhides it.

- [ ] **Step 4: Run tests**

Run: `python3 -m unittest tests.test_player_chrome tests.test_static_pages tests.test_library -v`

Expected: PASS. If `TestLibraryUIContract` still requires three tabs only, leave nav for Task 6.

- [ ] **Step 5: Commit**

```bash
git add web/index.html web/commute.html web/library.html web/app.js web/styles.css tests/test_player_chrome.py
git commit -m "$(cat <<'EOF'
feat: hide commute player until Play and add a mini bar

EOF
)"
```

---

### Task 4: Assignments merge (Python)

**Files:**
- Create: `scripts/assignments.py`
- Create: `data/assignments.json`
- Create: `data/roadmap_layout.json`
- Test: `tests/test_assignments.py`

**Interfaces:**
- Consumes: station nodes with `do` / `parallel` / `skim` / `project` id lists
- Produces: `RAILS`, `load_assignments(path)`, `validate_assignments(blob) -> list[str]` (errors), `apply_placements(nodes, placements) -> list[dict]`, `load_layout(path)`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_assignments.py
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from assignments import apply_placements, validate_assignments
from library import unassigned


def nodes():
    return [
        {
            "id": "s-a",
            "do": ["r-seed"],
            "parallel": [],
            "skim": [],
            "project": [],
        }
    ]


class TestApplyPlacements(unittest.TestCase):
    def test_given_missing_key_when_merged_then_seed_kept(self):
        out = apply_placements(nodes(), {})
        self.assertEqual(out[0]["do"], ["r-seed"])

    def test_given_placement_when_merged_then_moves_to_rail(self):
        out = apply_placements(nodes(), {"r-harvest": {"station": "s-a", "rail": "parallel"}})
        self.assertIn("r-harvest", out[0]["parallel"])
        self.assertEqual(out[0]["do"], ["r-seed"])

    def test_given_tombstone_when_merged_then_stripped_from_seed(self):
        out = apply_placements(nodes(), {"r-seed": None})
        self.assertEqual(out[0]["do"], [])

    def test_given_move_when_merged_then_not_duplicated(self):
        out = apply_placements(nodes(), {"r-seed": {"station": "s-a", "rail": "skim"}})
        self.assertEqual(out[0]["do"], [])
        self.assertEqual(out[0]["skim"], ["r-seed"])

    def test_given_unknown_station_when_merged_then_skipped(self):
        out = apply_placements(nodes(), {"r-x": {"station": "s-nope", "rail": "do"}})
        self.assertEqual(out[0]["do"], ["r-seed"])

    def test_given_bad_rail_when_validated_then_error(self):
        errs = validate_assignments(
            {"schema_version": 1, "placements": {"r-x": {"station": "s-a", "rail": "must"}}}
        )
        self.assertTrue(errs)

    def test_given_placement_when_unassigned_then_not_library(self):
        resources = [
            {"id": "r-seed", "title": "Seed", "url": "https://ex.com/s", "source": "curated"},
            {"id": "r-harvest", "title": "H", "url": "https://ex.com/h", "source": "awesome-ml.md"},
        ]
        graph = {"nodes": apply_placements(nodes(), {"r-harvest": {"station": "s-a", "rail": "parallel"}})}
        ids = {r["id"] for r in unassigned(resources, graph)}
        self.assertNotIn("r-harvest", ids)
        self.assertNotIn("r-seed", ids)

    def test_given_tombstone_when_unassigned_then_library(self):
        resources = [{"id": "r-seed", "title": "Seed", "url": "https://ex.com/s", "source": "curated"}]
        graph = {"nodes": apply_placements(nodes(), {"r-seed": None})}
        ids = {r["id"] for r in unassigned(resources, graph)}
        self.assertEqual(ids, {"r-seed"})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_assignments -v`

Expected: FAIL (`ModuleNotFoundError: assignments`).

- [ ] **Step 3: Implement `scripts/assignments.py` and seed JSON**

```python
"""Catalog overlay: resource id → station rail or Library tombstone."""

from __future__ import annotations

import json
from pathlib import Path

RAILS = ("do", "parallel", "skim", "project")
ROOT = Path(__file__).resolve().parents[1]
ASSIGNMENTS_PATH = ROOT / "data" / "assignments.json"
LAYOUT_PATH = ROOT / "data" / "roadmap_layout.json"


def empty_assignments() -> dict:
    return {"schema_version": 1, "placements": {}}


def empty_layout() -> dict:
    return {"schema_version": 1, "checkpoints": {}, "clusters": {}}


def load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    blob = json.loads(path.read_text())
    return blob if isinstance(blob, dict) else default


def load_assignments(path: Path | None = None) -> dict:
    blob = load_json(path or ASSIGNMENTS_PATH, empty_assignments())
    placements = blob.get("placements")
    if not isinstance(placements, dict):
        placements = {}
    return {"schema_version": 1, "placements": placements}


def load_layout(path: Path | None = None) -> dict:
    blob = load_json(path or LAYOUT_PATH, empty_layout())
    checkpoints = blob.get("checkpoints") if isinstance(blob.get("checkpoints"), dict) else {}
    clusters = blob.get("clusters") if isinstance(blob.get("clusters"), dict) else {}
    return {"schema_version": 1, "checkpoints": checkpoints, "clusters": clusters}


def validate_assignments(blob: object) -> list[str]:
    if not isinstance(blob, dict):
        return ["object required"]
    placements = blob.get("placements")
    if placements is None:
        return ["placements required"]
    if not isinstance(placements, dict):
        return ["placements must be an object"]
    errs: list[str] = []
    for rid, val in placements.items():
        if not isinstance(rid, str) or not rid:
            errs.append("empty resource id")
            continue
        if val is None:
            continue
        if not isinstance(val, dict):
            errs.append(f"{rid}: placement must be object or null")
            continue
        if val.get("station") in (None, ""):
            errs.append(f"{rid}: station required")
        if val.get("rail") not in RAILS:
            errs.append(f"{rid}: rail must be one of {RAILS}")
    return errs


def apply_placements(nodes: list[dict], placements: dict) -> list[dict]:
    out = []
    for st in nodes:
        copied = dict(st)
        for rail in RAILS:
            copied[rail] = list(st.get(rail) or [])
        out.append(copied)
    by_id = {st["id"]: st for st in out}

    def strip(rid: str) -> None:
        for st in out:
            for rail in RAILS:
                st[rail] = [x for x in st[rail] if x != rid]

    for rid, val in (placements or {}).items():
        if not isinstance(rid, str):
            continue
        strip(rid)
        if val is None:
            continue
        if not isinstance(val, dict):
            continue
        station = by_id.get(val.get("station"))
        rail = val.get("rail")
        if station is None or rail not in RAILS:
            continue
        if rid not in station[rail]:
            station[rail].append(rid)
    return out
```

Write:

`data/assignments.json`:

```json
{
  "schema_version": 1,
  "placements": {}
}
```

`data/roadmap_layout.json`:

```json
{
  "schema_version": 1,
  "checkpoints": {},
  "clusters": {}
}
```

- [ ] **Step 4: Run tests**

Run: `python3 -m unittest tests.test_assignments -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/assignments.py tests/test_assignments.py data/assignments.json data/roadmap_layout.json
git commit -m "$(cat <<'EOF'
feat: merge assignment overlay onto station rails

EOF
)"
```

---

### Task 5: Compile applies assignments

**Files:**
- Modify: `scripts/compile_catalog.py`
- Modify: `scripts/weekly_onboard.py` (comment/guard only if needed)
- Test: `tests/test_assignments.py` (add compile integration) and `tests/test_library.py` weekly module test

**Interfaces:**
- Consumes: `apply_placements`, `load_assignments`
- Produces: `graph.json` nodes after overlay

- [ ] **Step 1: Write the failing test**

In `tests/test_assignments.py`:

```python
    def test_given_compile_source_when_read_then_applies_placements(self):
        text = (Path(__file__).resolve().parents[1] / "scripts" / "compile_catalog.py").read_text()
        self.assertIn("apply_placements", text)
        self.assertIn("load_assignments", text)
```

In `tests/test_library.py` `test_given_weekly_module_when_read_then_does_not_edit_ranked_tracks`, add:

```python
        self.assertNotIn("assignments.json", text)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_assignments.TestApplyPlacements.test_given_compile_source_when_read_then_applies_placements -v`

Expected: FAIL (`apply_placements` not in compile).

- [ ] **Step 3: Wire compile**

In `scripts/compile_catalog.py`, import:

```python
from assignments import apply_placements, load_assignments
```

After the `for st in STATIONS: nodes.append({... resolve ...})` loop, before building `graph`:

```python
    nodes = apply_placements(nodes, load_assignments()["placements"])
```

Do not change harvest upsert or `graph_spec.py`.

- [ ] **Step 4: Run tests + compile**

Run:

```bash
python3 -m unittest tests.test_assignments tests.test_library.TestWeeklyOnboardSeam.test_given_weekly_module_when_read_then_does_not_edit_ranked_tracks -v
python3 scripts/compile_catalog.py
python3 scripts/validate.py
```

Expected: PASS; validate still ≥500 URLs. Empty placements leave graph identical to seed.

- [ ] **Step 5: Commit**

```bash
git add scripts/compile_catalog.py tests/test_assignments.py tests/test_library.py data/graph.json
git commit -m "$(cat <<'EOF'
feat: compile station rails through assignments overlay

EOF
)"
```

Only include `data/graph.json` if compile changed it (empty overlay should be a no-op; skip that file if unchanged).

---

### Task 6: Serve PUT + Roadmap route + static export

**Files:**
- Modify: `scripts/serve.py`, `scripts/atlas_paths.py`, `scripts/export_static.py`
- Create: `web/roadmap.html` (shell; canvas filled in Task 7)
- Test: `tests/test_static_pages.py`, `tests/test_library.py` nav tests, `tests/test_serve.py`

**Interfaces:**
- Consumes: `validate_assignments`, `apply_placements`, `load_assignments`
- Produces: `GET /roadmap` → `web/roadmap.html`; `PUT /data/assignments.json` (loopback, merge graph, return `{graph, assignments}`); `PUT /data/roadmap_layout.json`

- [ ] **Step 1: Write the failing tests**

Extend `tests/test_static_pages.py`:

```python
        self.assertEqual(atlas_root("/roadmap.html"), "/")
        self.assertEqual(atlas_root("/ai-sme-map/roadmap.html"), "/ai-sme-map/")
```

in `test_given_request_paths_when_atlas_root_then_data_dir_is_site_root`.

In `TestServePublicPaths`:

```python
        self.assertEqual(resolve_public_path("/roadmap"), "/web/roadmap.html")
        self.assertEqual(resolve_public_path("/roadmap.html"), "/web/roadmap.html")
```

In `TestRelativeAssets`, include `"roadmap.html"` in the HTML names loop.

In `TestExportStatic`, assert `roadmap.html`, `roadmap.js` (add a stub file in this task: empty module `export {}` or a comment file — Task 7 fills it), `data/assignments.json`, `data/roadmap_layout.json`.

Change `tests/test_library.py` `test_given_nav_when_read_then_three_tabs_on_each_page` to loop `("index.html", "commute.html", "library.html", "roadmap.html")` and require `href="roadmap.html"` plus the word `Roadmap` on each page.

Add to `tests/test_serve.py`:

```python
    def test_put_paths_include_assignments_and_layout(self):
        import inspect
        import serve

        src = inspect.getsource(serve.Handler.do_PUT)
        self.assertIn("/data/assignments.json", src)
        self.assertIn("/data/roadmap_layout.json", src)
        self.assertIn("LOOPBACK", src)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_static_pages tests.test_serve tests.test_library.TestLibraryUIContract.test_given_nav_when_read_then_three_tabs_on_each_page -v`

Expected: FAIL (no roadmap stem / file).

- [ ] **Step 3: Implement routes, PUT, shell page, nav, export**

`scripts/atlas_paths.py`: `PAGE_STEMS = frozenset({"index", "commute", "library", "roadmap"})`.

`scripts/serve.py` `PUBLIC_ALIASES` add `/roadmap` and `/roadmap.html`.

PUT: parse path; allow `/data/progress.json` (existing), `/data/assignments.json`, `/data/roadmap_layout.json`. All three 403 off loopback.

For assignments:

```python
        errs = validate_assignments(payload)
        if errs:
            self.send_error(400, errs[0])
            return
        payload.setdefault("schema_version", 1)
        payload.setdefault("placements", {})
        ASSIGNMENTS.write_text(json.dumps(payload, indent=2) + "\n")
        graph = load_json(ROOT / "data" / "graph.json", {"nodes": []})
        graph["nodes"] = apply_placements(graph["nodes"], payload["placements"])
        (ROOT / "data" / "graph.json").write_text(json.dumps(graph, indent=2) + "\n")
        return self._json(200, {"assignments": payload, "graph": graph})
```

**Bug to avoid:** applying placements onto already-merged `graph.json` would double-apply. PUT must merge against **seed** rails, not against current graph.

Fix: store seed rails in graph at compile time as `graph["seed_nodes"]` **or** re-resolve from `graph_spec` on PUT **or** write `data/graph.seed.json`.

Locked choice: compile writes `data/graph.seed.json` as the pre-overlay nodes (same shape as `nodes`). Overlay PUT and compile both do `apply_placements(seed_nodes, placements)`. Public export copies `graph.json` (merged) only, not `graph.seed.json` if you want to hide seed — **export `graph.json` merged; also export `graph.seed.json` is unnecessary on Pages**. Keep `graph.seed.json` local for PUT.

Compile:

```python
    seed_nodes = nodes  # after resolve, before overlay
    (DATA / "graph.seed.json").write_text(json.dumps({"nodes": seed_nodes}, indent=2) + "\n")
    nodes = apply_placements(seed_nodes, load_assignments()["placements"])
```

PUT loads `graph.seed.json`, applies placements, writes `graph.json`. If seed file missing, 500/400 with a clear error.

Add `graph.seed.json` to `.gitignore` **only if** it is a build artifact. It is a compile output like `graph.json`, which **is** committed. Commit `graph.seed.json` as well so a fresh clone can PUT without compiling first — **or** have PUT run resolve from `graph_spec` if seed missing.

Locked: compile writes `data/graph.seed.json` and it is committed next to `graph.json`. Export static does **not** copy `graph.seed.json` (Pages cannot PUT).

Layout PUT: validate object with `checkpoints` / `clusters` dicts (empty allowed); write file; return blob. No graph rewrite.

`web/roadmap.html` shell: same fonts/css as library, `data-page="roadmap"`, mast nav with Roadmap current, `#map.roadmap-board`, `#drawer`, player aside (hidden, same controls as Task 3), then:

```html
  <script src="app.js" type="module"></script>
  <script src="roadmap.js" type="module"></script>
```

`web/roadmap.js` stub:

```javascript
// Canvas filled in Task 7. Keep this file present for export tests.
```

Nav on `index.html`, `commute.html`, `library.html`, `roadmap.html`:

```html
        <a href="index.html">Tonight</a>
        <a href="commute.html">Commute · eyes-off</a>
        <a href="library.html">Library · unassigned</a>
        <a href="roadmap.html">Roadmap</a>
```

Set `aria-current="page"` on the active one. Rename the library test method if you want; keeping the old method name is fine.

`export_static.py`:

```python
WEB_FILES = ("index.html", "commute.html", "library.html", "roadmap.html", "app.js", "roadmap.js", "styles.css")
DATA_FILES = (..., "assignments.json", "roadmap_layout.json")
```

Do not export `graph.seed.json`.

- [ ] **Step 4: Run tests**

Run:

```bash
python3 scripts/compile_catalog.py
python3 -m unittest tests.test_static_pages tests.test_serve tests.test_library tests.test_assignments tests.test_player_chrome tests.test_focus -v
```

Expected: PASS. Rename note: `test_given_nav_when_read_then_three_tabs` still passes if it now asserts four hrefs.

- [ ] **Step 5: Commit**

```bash
git add scripts/serve.py scripts/atlas_paths.py scripts/export_static.py scripts/compile_catalog.py web/roadmap.html web/roadmap.js web/index.html web/commute.html web/library.html tests/test_static_pages.py tests/test_serve.py tests/test_library.py data/graph.json data/graph.seed.json
git commit -m "$(cat <<'EOF'
feat: localhost assignment PUT and Roadmap page shell

EOF
)"
```

---

### Task 7: Roadmap canvas (view)

**Files:**
- Modify: `web/roadmap.js`, `web/styles.css`, `web/app.js` (load layout JSON; expose state)
- Test: `tests/test_library.py` or `tests/test_roadmap.py` string contracts

**Interfaces:**
- Consumes: `state.graph`, `state.resources`, `state.progress`, `pinsOf`, `doIdsForStation`, `data/roadmap_layout.json`
- Produces: `renderRoadmap()`, pan/zoom, click-to-drawer; harvest clusters for `unassignedResources`

- [ ] **Step 1: Write the failing test**

`tests/test_roadmap.py`:

```python
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestRoadmapView(unittest.TestCase):
    def test_given_roadmap_js_when_read_then_canvas_primitives(self):
        js = (ROOT / "web" / "roadmap.js").read_text()
        self.assertIn("renderRoadmap", js)
        self.assertIn("MUST", js)
        self.assertIn("ELECTIVE", js)
        self.assertIn("MAY", js)
        self.assertIn("Build", js)
        self.assertIn("viewBox", js)
        self.assertIn("unassigned", js.lower())

    def test_given_roadmap_page_when_read_then_board_and_scripts(self):
        html = (ROOT / "web" / "roadmap.html").read_text()
        self.assertIn('data-page="roadmap"', html)
        self.assertIn('id="board"', html)
        self.assertIn('src="roadmap.js"', html)
```

Change `roadmap.html` `#map` to `<div id="board" class="roadmap-board"></div>` if not already.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_roadmap -v`

Expected: FAIL (`renderRoadmap` missing).

- [ ] **Step 3: Implement view**

In `web/app.js` `load()`, fetch `dataHref("roadmap_layout.json")` (default `{checkpoints:{}, clusters:{}}`) onto `state.layout`.

Export nothing; `roadmap.js` reads `window` via functions hung on `globalThis.atlas` at the end of `app.js`:

```javascript
globalThis.atlas = {
  get state() { return state; },
  $,
  PAGE,
  pinsOf,
  doIdsForStation,
  isComplete,
  unassignedResources,
  categoryOf, // if named differently, export the existing helper used by renderLibrary
  renderDrawer,
  persistAndRedraw,
  pinStationForCard,
  togglePin,
  saveLayout: async (layout) => { /* Task 8 */ },
  saveAssignments: async (blob) => { /* Task 8 */ },
  isAuthor: () => ["127.0.0.1", "localhost", "::1"].includes(location.hostname),
};
```

Use the real library helper names (`category_of` equivalent in JS — `categoryOf` / existing `source` grouping). If the helper is inline in `renderLibrary`, extract `categoryOf(row)` and `unassignedResources()` (already present).

`web/roadmap.js` (module): if `document.body.dataset.page !== "roadmap"` return.

Layout defaults:

```javascript
function checkpointPos(st, layout) {
  const hit = layout.checkpoints && layout.checkpoints[st.id];
  if (hit && typeof hit.x === "number") return hit;
  const x = 48 + (st.stage || 0) * 300;
  const y = st.rail === "theory" ? 56 : 460;
  return { x, y };
}

function clusterPos(key, index, layout) {
  const hit = layout.clusters && layout.clusters[key];
  if (hit && typeof hit.x === "number") return hit;
  return { x: 48 + 8 * 300, y: 56 + index * 240 };
}
```

Paint an SVG `viewBox="0 0 3600 2800"` inside `#board`. Inner `<g id="roadmap-world">`.

- Edges: for each station, for each `prereq`, line from prereq center-top to station.
- Checkpoint: `<g>` at `translate(x,y)`, title, four lanes. Lane ids: `do` labeled MUST, `parallel` ELECTIVE, `skim` MAY, `project` Build. Resource chips: 200×28 rects stacked, title truncated to ~28 chars, checkmark if `isComplete`, star if pin matches.
- Unassigned: `unassignedResources()` grouped by `categoryOf` / `source` filename. One cluster per group, all chips visible. Skip commute-assigned rows (already excluded by `unassigned`).

Pan: pointer drag on SVG background updates `translate` on `#roadmap-world`. Zoom: wheel `scale` around cursor (clamp 0.25–2.5). Fit button sets scale to 1 and translate 0.

Chip click: `preventDefault`, find resource id, if assigned `renderDrawer(station)` and set `active`; if unassigned, fill drawer with that card only.

`app.js` `redraw()`: if `PAGE === "roadmap"`, skip `renderMap`; call `globalThis.renderRoadmap?.()`. Define `globalThis.renderRoadmap = renderRoadmap` from `roadmap.js`.

CSS: `.roadmap-board svg { width: 100%; height: calc(100vh - 12rem); background: var(--ticket); border: 1px solid var(--ink); cursor: grab; }` Lane labels IBM Plex Mono 11px. Theory checkpoint left border `--theory`, practice `--practice`.

- [ ] **Step 4: Run tests**

Run: `python3 -m unittest tests.test_roadmap tests.test_static_pages tests.test_library -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/roadmap.js web/roadmap.html web/app.js web/styles.css tests/test_roadmap.py
git commit -m "$(cat <<'EOF'
feat: render the harvest graph on a pan-zoom Roadmap page

EOF
)"
```

---

### Task 8: Localhost drag writes overlay

**Files:**
- Modify: `web/roadmap.js`, `web/app.js`
- Test: `tests/test_roadmap.py`, `tests/test_serve.py`

**Interfaces:**
- Consumes: PUT from Task 6, `atlas.isAuthor()`, `apply_placements` on server
- Produces: drag resource to lane/cluster; drag group to update layout; Pages snap-back note

- [ ] **Step 1: Write the failing test**

```python
    def test_given_roadmap_js_when_read_then_authoring_hooks(self):
        js = (ROOT / "web" / "roadmap.js").read_text()
        self.assertIn("isAuthor", js)
        self.assertIn("assignments.json", js)
        self.assertIn("localhost-only", js)
        self.assertIn("placements", js)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_roadmap.TestRoadmapView.test_given_roadmap_js_when_read_then_authoring_hooks -v`

Expected: FAIL.

- [ ] **Step 3: Implement drag**

In `app.js`, implement the stubs:

```javascript
async function putJson(name, body) {
  const res = await fetch(dataHref(name), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(String(res.status));
  return res.json();
}
```

`saveAssignments` PUTs the full `{schema_version:1, placements}` object. On success, if payload has `graph`, `state.graph = data.graph`. `saveLayout` PUTs layout.

Keep `state.assignments` loaded in `load()` from `data/assignments.json`.

Drag chip (author only): on pointerup, hit-test lane (`data-drop-station` + `data-drop-rail`) or cluster (`data-drop-cluster`).

- Lane: `placements[id] = {station, rail}`; PUT; re-render.
- Cluster / Library: if id is in **seed** rails (`state.graphSeed` — load `graph.seed.json` on localhost only; on Pages skip), set `placements[id] = null`; else `delete placements[id]`; PUT; re-render.

On Pages or PUT throw: restore previous translate, set `#roadmap-note` text to `Assignments are localhost-only.`

Drag checkpoint header / cluster header: on pointerup, `layout.checkpoints[id] = {x,y}` or `layout.clusters[key] = {x,y}`; PUT layout (localhost). On Pages, allow temporary move then snap back with the same note.

Load `graph.seed.json` in `load()` with `.catch(() => null)` — missing on Pages is fine. Use it only for tombstone vs delete.

`weekly_onboard` already forbidden from touching assignments.

- [ ] **Step 4: Run tests**

Run: `python3 -m unittest discover -s tests -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/roadmap.js web/app.js tests/test_roadmap.py
git commit -m "$(cat <<'EOF'
feat: drag resources on Roadmap to write the catalog overlay

EOF
)"
```

---

### Task 9: Verify in browser and validate

**Files:** none required unless a bug shows up.

- [ ] **Step 1: `make validate`**

Run: `make validate`

Expected: compile + unittest + `validate.py` + first-run + sync-check all exit 0. First-run Focus still Essence of Linear Algebra / Vectors (no pins in empty progress).

- [ ] **Step 2: Browser (localhost)**

`make serve` → `http://127.0.0.1:7432`

1. Tonight: no player chrome. Star a Parallel course on the current station → Focus title becomes that course. Mark it done → Focus returns to compiled Do[0].
2. Commute: Play an episode → deck visible. Open Tonight → mini-player with same title. Expand / Mini / Dismiss. Dismiss hides chrome. Reload Tonight: still no player.
3. Roadmap: pan/zoom, checkpoints, harvest clusters with many chips. Drag a Library chip onto MUST of “See matrices” → Tonight drawer Do list includes it after reload. Git shows `data/assignments.json` dirty.
4. Confirm Pages path is not required for this step.

- [ ] **Step 3: Commit only if Step 2 forced fixes**

If you changed files to fix bugs, commit with a message that names the bug (`fix: snap Roadmap drag back when PUT is 403`). If nothing changed, do not create an empty commit.

---

## Self-review

**Spec coverage**
- Pins + Focus + drawer order → Tasks 1–2
- Mini-player session / defaults / dismiss → Task 3
- Overlay merge, tombstone, compile → Tasks 4–5
- PUT, seed graph, export, nav → Task 6
- Canvas every-URL, lanes, clusters, pan/zoom → Task 7
- Drag authoring localhost-only → Task 8
- Browser proof → Task 9

**Placeholders:** none.

**Types:** `placements[id]` is `null | {station, rail}` with `rail in do|parallel|skim|project`. Pins are `{[stationId]: resourceId}` on `progress.pins`. Player session is `{id, playing}`.
