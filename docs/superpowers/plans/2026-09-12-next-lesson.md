# Next Lesson + Containment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Beginner Focus is the next unfinished lesson of the current station’s first Do item, with per-lesson ticks and parent/child containment rollup.

**Architecture:** `scripts/focus.py` is the single algorithm (complete, rollup, next). Compile attaches `parts` / `parent_id` from `scripts/outlines.py`. `serve.py` exposes `GET /data/focus.json` and rollups on PUT. The timetable UI renders a Focus strip and nested lesson rows. No harvest explosion; no substitute-course edges.

**Tech Stack:** Python 3 stdlib (`unittest`, existing compile/validate/http.server), static `web/app.js`.

## Global Constraints

- Catalog floor remains ≥500 unique http(s) URLs; slug-only parts are progress keys, not catalog rows.
- Duplicate means containment only: parent done covers parts; parts listed in outlines only (no URL-prefix scrape).
- Focus uses `station.do[0]` only; later Do items stay in the drawer and in `nDone/nDo` but do not block Next.
- Allowed progress values stay `todo` | `doing` | `skimmed` | `done`.
- Do not scrape Coursera, YouTube, or cookies. Verify live TOCs before committing lesson URLs.
- Atlas lives in `~/dev/ai-sme-map`, not dealradar. Do not commit secrets. Restart LaunchAgent after `serve.py` changes.

---

### Task 1: Focus algorithm (atomic resources)

**Files:**
- Create: `scripts/focus.py`
- Create: `tests/test_focus.py`

**Interfaces:**
- Consumes: in-memory `graph` (`nodes[].do` id lists), `resources` (list of dicts with `id`, `title`, `url`, optional `parts`, optional `parent_id`), `progress` (`dict[str, str]`).
- Produces:
  - `STATUS = ("todo", "doing", "skimmed", "done")`
  - `is_complete(progress, resource_id, by_id) -> bool`
  - `apply_status(progress, by_id, resource_id, status) -> dict` (new progress map)
  - `next_focus(graph, resources, progress) -> dict | None` where the dict is `{station_id, station_title, resource_id, resource_title, part_id, part_title, url, label, done}` and `None` is not used; atlas complete returns `{"done": True}`.

- [ ] **Step 1: Write the failing tests**

```python
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from focus import apply_status, is_complete, next_focus


def by_id(resources):
    return {r["id"]: r for r in resources}


GRAPH = {
    "nodes": [
        {"id": "s-a", "title": "See matrices", "do": ["r-3b1b"]},
        {"id": "s-b", "title": "Work matrices", "do": ["r-imperial", "r-strang"]},
    ]
}
RES = [
    {"id": "r-3b1b", "title": "Essence of LA", "url": "https://3blue1brown.com/topics/linear-algebra"},
    {"id": "r-imperial", "title": "Imperial LA", "url": "https://coursera.org/learn/linear-algebra-machine-learning"},
    {"id": "r-strang", "title": "18.06", "url": "https://ocw.mit.edu/18-06"},
]


class TestAtomicFocus(unittest.TestCase):
    def test_next_is_first_station_primary(self):
        f = next_focus(GRAPH, RES, {})
        self.assertEqual(f["station_id"], "s-a")
        self.assertEqual(f["resource_id"], "r-3b1b")
        self.assertIsNone(f["part_id"])
        self.assertEqual(f["url"], RES[0]["url"])
        self.assertFalse(f.get("done"))

    def test_completing_primary_skips_later_do_on_same_station(self):
        f = next_focus(GRAPH, RES, {"r-3b1b": "done"})
        self.assertEqual(f["station_id"], "s-b")
        self.assertEqual(f["resource_id"], "r-imperial")

    def test_later_do_does_not_block_focus(self):
        f = next_focus(GRAPH, RES, {"r-3b1b": "done", "r-imperial": "done"})
        self.assertTrue(f.get("done"))
        self.assertNotEqual(f.get("resource_id"), "r-strang")

    def test_skimmed_is_not_complete(self):
        self.assertFalse(is_complete({"r-3b1b": "skimmed"}, "r-3b1b", by_id(RES)))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_focus -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'focus'` (or `cannot import name next_focus`).

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/focus.py
from __future__ import annotations

STATUS = ("todo", "doing", "skimmed", "done")


def by_id(resources: list[dict]) -> dict[str, dict]:
    return {r["id"]: r for r in resources}


def is_complete(progress: dict, resource_id: str, resources_by_id: dict) -> bool:
    rec = resources_by_id.get(resource_id) or {}
    if progress.get(resource_id) == "done":
        return True
    parts = rec.get("parts") or []
    if parts and all(is_complete(progress, p["id"], resources_by_id) for p in parts):
        return True
    parent_id = rec.get("parent_id")
    if parent_id and progress.get(parent_id) == "done":
        return True
    return False


def apply_status(progress: dict, resources_by_id: dict, resource_id: str, status: str) -> dict:
    if status not in STATUS:
        raise ValueError(status)
    out = dict(progress)
    out[resource_id] = status
    rec = resources_by_id.get(resource_id) or {}
    parts = rec.get("parts") or []
    if status == "done":
        for p in parts:
            out[p["id"]] = "done"
        parent_id = rec.get("parent_id")
        if parent_id:
            parent = resources_by_id.get(parent_id) or {}
            parent_parts = parent.get("parts") or []
            if parent_parts and all(out.get(p["id"]) == "done" for p in parent_parts):
                out[parent_id] = "done"
    else:
        parent_id = rec.get("parent_id")
        if parent_id and out.get(parent_id) == "done":
            out[parent_id] = "doing"
    return out


def next_focus(graph: dict, resources: list[dict], progress: dict) -> dict:
    resources_by_id = by_id(resources)
    for station in graph["nodes"]:
        do = station.get("do") or []
        if not do:
            continue
        primary_id = do[0]
        rec = resources_by_id[primary_id]
        if rec.get("parts"):
            for part in rec["parts"]:
                if not is_complete(progress, part["id"], resources_by_id):
                    return _focus(station, rec, part)
            if not is_complete(progress, primary_id, resources_by_id):
                return _focus(station, rec, None)
            continue
        if not is_complete(progress, primary_id, resources_by_id):
            return _focus(station, rec, None)
    return {"done": True}


def _focus(station: dict, rec: dict, part: dict | None) -> dict:
    title = (part or {}).get("title") or rec["title"]
    url = (part or {}).get("url") or rec.get("url")
    label = rec["title"] if not part else f"{rec['title']} · {part['title']}"
    return {
        "done": False,
        "station_id": station["id"],
        "station_title": station["title"],
        "resource_id": rec["id"],
        "resource_title": rec["title"],
        "part_id": None if part is None else part["id"],
        "part_title": None if part is None else part["title"],
        "url": url,
        "label": label,
    }
```

- [ ] **Step 4: Run tests and make sure they pass**

Run: `python3 -m unittest tests.test_focus -v`

Expected: `OK` (3 tests in this task; `test_skimmed` included).

- [ ] **Step 5: Commit**

```bash
git add scripts/focus.py tests/test_focus.py
git commit -m "$(cat <<'EOF'
Add Focus picker that advances on the station's first Do item.

EOF
)"
```

---

### Task 2: Containment rollup and part-level Focus

**Files:**
- Modify: `scripts/focus.py` (already has hooks; this task locks rollup tests)
- Modify: `tests/test_focus.py`

**Interfaces:**
- Consumes: `parts` on the parent; child dicts in `resources` with `parent_id` and `id` matching `part["id"]` when the lesson is also a catalog row.
- Produces: same functions as Task 1; `is_complete` treats parent-done as covering parts; `apply_status` implements the spec table.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_focus.py`)

```python
PARENT = {
    "id": "r-fastai",
    "title": "fast.ai part 1",
    "url": "https://course.fast.ai",
    "parts": [
        {"id": "r-fastai:lesson1", "title": "Lesson 1", "url": "https://course.fast.ai/Lessons/lesson1.html"},
        {"id": "r-fastai:lesson2", "title": "Lesson 2", "url": "https://course.fast.ai/Lessons/lesson2.html"},
    ],
}
CHILD = {
    "id": "r-fastai:lesson1",
    "title": "Lesson 1",
    "url": "https://course.fast.ai/Lessons/lesson1.html",
    "parent_id": "r-fastai",
    "kind": "lesson",
}
GRAPH2 = {"nodes": [{"id": "s-dl", "title": "Ship a net", "do": ["r-fastai"]}]}
RES2 = [PARENT, CHILD]


class TestParts(unittest.TestCase):
    def test_next_is_first_unfinished_part(self):
        f = next_focus(GRAPH2, RES2, {})
        self.assertEqual(f["part_id"], "r-fastai:lesson1")
        self.assertEqual(f["url"], CHILD["url"])

    def test_parent_done_covers_parts(self):
        bid = by_id(RES2)
        self.assertTrue(is_complete({"r-fastai": "done"}, "r-fastai:lesson1", bid))
        f = next_focus(GRAPH2, RES2, {"r-fastai": "done"})
        self.assertTrue(f.get("done"))

    def test_all_parts_done_completes_parent(self):
        bid = by_id(RES2)
        progress = {"r-fastai:lesson1": "done", "r-fastai:lesson2": "done"}
        self.assertTrue(is_complete(progress, "r-fastai", bid))

    def test_mark_parent_done_writes_parts(self):
        out = apply_status({}, by_id(RES2), "r-fastai", "done")
        self.assertEqual(out["r-fastai"], "done")
        self.assertEqual(out["r-fastai:lesson1"], "done")
        self.assertEqual(out["r-fastai:lesson2"], "done")

    def test_unchecking_part_uncompletes_parent(self):
        start = apply_status({}, by_id(RES2), "r-fastai", "done")
        out = apply_status(start, by_id(RES2), "r-fastai:lesson2", "todo")
        self.assertEqual(out["r-fastai"], "doing")
        self.assertEqual(out["r-fastai:lesson1"], "done")

    def test_last_part_marks_parent(self):
        start = {"r-fastai:lesson1": "done"}
        out = apply_status(start, by_id(RES2), "r-fastai:lesson2", "done")
        self.assertEqual(out["r-fastai"], "done")
```

- [ ] **Step 2: Run test to verify new tests fail if rollup is incomplete**

Run: `python3 -m unittest tests.test_focus.TestParts -v`

Expected: FAIL only if Task 1 implementation omitted part loops; if Task 1 already included them, this step is green — do not regress. If `test_unchecking_part_uncompletes_parent` fails, fix `apply_status` as in Task 1.

- [ ] **Step 3: Adjust `apply_status` so un-doing a part never leaves parent `done`**

Already specified in Task 1. If parent has no `parts` lookup when the clicked id is a child-only progress key, resolve via `parent_id` on the child resource **or** parse nothing — children must be in `resources` when they have URLs; slug-only parts exist only on `parent["parts"]`. For slug-only ids not in `by_id`, find the parent by scanning `parts`:

```python
def parent_of(resource_id: str, resources_by_id: dict) -> dict | None:
    rec = resources_by_id.get(resource_id)
    if rec and rec.get("parent_id"):
        return resources_by_id.get(rec["parent_id"])
    for r in resources_by_id.values():
        for p in r.get("parts") or []:
            if p["id"] == resource_id:
                return r
    return None
```

Use `parent_of` in `is_complete` and `apply_status` so slug-only weeks roll up.

- [ ] **Step 4: Run tests**

Run: `python3 -m unittest tests.test_focus -v`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/focus.py tests/test_focus.py
git commit -m "$(cat <<'EOF'
Roll up lesson ticks to parent courses and cover parts when a parent is done.

EOF
)"
```

---

### Task 3: Outline table + compile wiring

**Files:**
- Create: `scripts/outlines.py`
- Modify: `scripts/compile_catalog.py` (`upsert` + after `resources` built, attach parts)
- Modify: `scripts/validate.py`
- Create: `tests/test_outlines_compile.py`

**Interfaces:**
- Consumes: `OUTLINES: dict[str, list[dict]]` keyed by **raw parent URL** (compile will `normalize`).
- Each part: `{slug: str, title: str, url: str | None}`.
- Produces: parent resource fields `parts: [{id, title, url}]` with `id = parent_id + ":" + slug`; child catalog rows when `url` is set (`kind="lesson"`, `parent_id`, `featured=False`); `parent_id` on matching existing URLs.

- [ ] **Step 1: Write the failing compile test**

```python
import json
import tempfile
import unittest
from pathlib import Path
import sys

# Prefer testing attach_outlines as a function. If compile_catalog has no
# attach_outlines yet, this import fails — that is the failing test.

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


class TestAttachOutlines(unittest.TestCase):
    def test_slug_only_part_is_not_a_catalog_url(self):
        from compile_catalog import attach_outlines, make_id, normalize

        parent_url = normalize("https://coursera.org/specializations/machine-learning-introduction")
        parent = {
            "id": make_id(parent_url),
            "title": "Ng spec",
            "url": parent_url,
            "kind": "course",
            "featured": True,
            "source": "curated",
        }
        outlines = {parent_url: [{"slug": "week-1", "title": "Week 1", "url": None}]}
        resources = attach_outlines([parent], outlines)
        self.assertEqual(len(resources), 1)
        self.assertEqual(resources[0]["parts"][0]["id"], f"{parent['id']}:week-1")
        self.assertIsNone(resources[0]["parts"][0]["url"])

    def test_url_part_upserts_lesson_row(self):
        from compile_catalog import attach_outlines, make_id, normalize

        parent_url = normalize("https://course.fast.ai")
        lesson_url = normalize("https://course.fast.ai/Lessons/lesson1.html")
        parent = {
            "id": make_id(parent_url),
            "title": "fast.ai",
            "url": parent_url,
            "kind": "course",
            "featured": True,
            "source": "curated",
        }
        outlines = {
            parent_url: [{"slug": "lesson1", "title": "Lesson 1", "url": lesson_url}]
        }
        resources = attach_outlines([parent], outlines)
        ids = {r["id"] for r in resources}
        self.assertEqual(len(resources), 2)
        child = next(r for r in resources if r["url"] == lesson_url)
        self.assertEqual(child["kind"], "lesson")
        self.assertEqual(child["parent_id"], parent["id"])
        self.assertEqual(child["id"], f"{parent['id']}:lesson1")
        self.assertIn(child["id"], ids)
```

Note: child `id` must be `parent_id:slug`, **not** `make_id(lesson_url)`, so progress keys stay stable if the lesson URL was already a harvest row. `attach_outlines` must rewrite an existing harvest row’s `id` to the part id **or** keep `make_id(url)` and store part id separately.

**Locked rule:** part progress key is always `parent_id + ":" + slug`. If a harvest row already exists for the lesson URL, keep that row’s `id` as `make_id(url)` for catalog uniqueness of ids, and set `parent_id`. The `parts[].id` is still `parent_id:slug`. `is_complete` must treat **either** `parts[].id` **or** the catalog row id as the same completion if we alias them.

Simpler locked rule to avoid alias bugs: **if the lesson URL already has a catalog id, `parts[].id` is that catalog `make_id(url)`**. If `url` is null, `parts[].id` is `parent_id:slug`. Update Task 2 tests if needed so `r-fastai:lesson1` remains valid as a synthetic id when we control the fixture.

For compile: 

```python
def part_id(parent: dict, slug: str, part_url: str | None, url_to_id: dict, make_id, normalize) -> str:
    if part_url:
        nu = normalize(part_url)
        if nu in url_to_id:
            return url_to_id[nu]
        return make_id(nu)
    return f"{parent['id']}:{slug}"
```

When upserting a new lesson URL, `id = make_id(url)` and also record `parent_id`. Then `parts[].id = that id`. Synthetic weeks stay `parent:slug`.

Update `TestParts` to use `make_id` only in fixtures; keep `r-fastai:lesson1` as synthetic — both forms must work in `is_complete`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_outlines_compile -v`

Expected: FAIL `cannot import name 'attach_outlines'`.

- [ ] **Step 3: Implement `attach_outlines` and call it from `main()`**

Add to `compile_catalog.py` (after `url_to_id` is first built, before writing JSON):

```python
def attach_outlines(resources: list[dict], outlines: dict) -> list[dict]:
    from outlines import OUTLINES as _default
    outlines = outlines if outlines is not None else _default
    by_url = {r["url"]: r for r in resources}

    def norm_key(u: str) -> str:
        return normalize(u)

    keyed = {norm_key(k): v for k, v in outlines.items()}
    extra = []
    for rec in resources:
        spec = keyed.get(rec["url"])
        if not spec:
            continue
        parts = []
        for item in spec:
            slug = item["slug"]
            raw_url = item.get("url")
            if raw_url:
                nurl = normalize(raw_url)
                child = by_url.get(nurl)
                if child is None:
                    child = {
                        "id": make_id(nurl),
                        "title": item["title"],
                        "url": nurl,
                        "kind": "lesson",
                        "provider": rec.get("provider") or "",
                        "access": rec.get("access") or "free",
                        "level": rec.get("level") or "unspecified",
                        "pedagogy": rec.get("pedagogy") or [],
                        "branches": rec.get("branches") or [],
                        "evidence": f"Lesson of {rec['title']}",
                        "featured": False,
                        "source": "outline",
                        "parent_id": rec["id"],
                    }
                    extra.append(child)
                    by_url[nurl] = child
                else:
                    child["parent_id"] = rec["id"]
                    if child.get("kind") in (None, "course", "article"):
                        pass  # do not demote a featured course that shares a URL
                parts.append({"id": child["id"], "title": item["title"], "url": nurl})
            else:
                parts.append({"id": f"{rec['id']}:{slug}", "title": item["title"], "url": None})
        rec["parts"] = parts
    return resources + extra
```

In `main()`, after the harvest upsert loop:

```python
from outlines import OUTLINES
resources = sorted(by_url.values(), key=lambda r: (not r["featured"], r["title"].lower()))
resources = attach_outlines(resources, OUTLINES)
url_to_id = {r["url"]: r["id"] for r in resources}
```

Create `scripts/outlines.py` with `OUTLINES: dict = {}` for this task (empty is valid).

Validate: every `parts[].id` either equals some resource id or matches `{parent_id}:{slug}`; every `parts[].url` that is not null exists in the catalog; no part lists a different parent as its own parent (no cycles).

```python
# in validate.py, after dangling rail checks
for r in resources:
    for p in r.get("parts") or []:
        if p.get("url") and p["url"] not in set(urls):
            errors.append(f"{r['id']} part missing catalog url {p['url']}")
        pid = p["id"]
        if pid not in ids and not pid.startswith(r["id"] + ":"):
            errors.append(f"{r['id']} bad part id {pid}")
        if p["id"] == r["id"]:
            errors.append(f"{r['id']} part id equals parent")
```

- [ ] **Step 4: Run tests + validate**

Run:

```bash
python3 -m unittest tests.test_outlines_compile tests.test_focus -v
python3 scripts/compile_catalog.py
python3 scripts/validate.py
```

Expected: tests `OK`; validate `OK` with resource count ≥ previous (empty outlines ⇒ same count).

- [ ] **Step 5: Commit**

```bash
git add scripts/outlines.py scripts/compile_catalog.py scripts/validate.py tests/test_outlines_compile.py
git commit -m "$(cat <<'EOF'
Attach optional lesson outlines at compile time without exploding the harvest.

EOF
)"
```

---

### Task 4: Seed first outlines (verify URLs live)

**Files:**
- Modify: `scripts/outlines.py`

**Interfaces:**
- Consumes: parent URLs already in `CURATED` / compile (`https://www.3blue1brown.com/topics/linear-algebra` normalizes by stripping `www`).
- Produces: `OUTLINES` entries for (1) 3Blue1Brown Essence of LA, (2) fast.ai part 1 lessons that 200, (3) slug-only Ng weeks, (4) slug-only Imperial LA weeks. Zero to Hero can wait if lecture URLs are messy — skip rather than 404.

- [ ] **Step 1: Confirm live lesson URLs**

Run (expect HTTP 200; drop any that are not):

```bash
python3 - <<'PY'
from urllib.request import Request, urlopen
urls = [
  "https://www.3blue1brown.com/lessons/vectors",
  "https://www.3blue1brown.com/lessons/span",
  "https://www.3blue1brown.com/lessons/linear-transformations",
  "https://www.3blue1brown.com/lessons/matrix-multiplication",
  "https://www.3blue1brown.com/lessons/3d-transformations",
  "https://www.3blue1brown.com/lessons/determinant",
  "https://www.3blue1brown.com/lessons/inverse-matrices",
  "https://www.3blue1brown.com/lessons/nonsquare-matrices",
  "https://www.3blue1brown.com/lessons/dot-products",
  "https://www.3blue1brown.com/lessons/cross-products",
  "https://www.3blue1brown.com/lessons/cross-products-extended",
  "https://www.3blue1brown.com/lessons/cramers-rule",
  "https://www.3blue1brown.com/lessons/change-of-basis",
  "https://www.3blue1brown.com/lessons/eigenvalues",
  "https://www.3blue1brown.com/lessons/abstract-vector-spaces",
  "https://course.fast.ai/Lessons/lesson1.html",
  "https://course.fast.ai/Lessons/lesson2.html",
  "https://course.fast.ai/Lessons/lesson3.html",
  "https://course.fast.ai/Lessons/lesson4.html",
  "https://course.fast.ai/Lessons/lesson5.html",
  "https://course.fast.ai/Lessons/lesson6.html",
  "https://course.fast.ai/Lessons/lesson7.html",
  "https://course.fast.ai/Lessons/lesson8.html",
]
for u in urls:
    try:
        r = urlopen(Request(u, headers={"User-Agent": "ai-sme-map"}), timeout=15)
        print(r.status, u)
    except Exception as e:
        print("FAIL", u, e)
PY
```

- [ ] **Step 2: Write `OUTLINES` using only URLs that returned 200; Ng/Imperial are slug-only**

Match parent keys to the **normalized** parent URLs already in `resources.json` (open that file and copy the `url` field for Essence of LA, fast.ai, Ng spec, Imperial LA). Example shape:

```python
OUTLINES = {
    "https://3blue1brown.com/topics/linear-algebra": [
        {"slug": "vectors", "title": "Vectors", "url": "https://www.3blue1brown.com/lessons/vectors"},
        # ... only 200s
    ],
    "https://course.fast.ai": [
        {"slug": "lesson1", "title": "Lesson 1", "url": "https://course.fast.ai/Lessons/lesson1.html"},
        # ...
    ],
    "https://coursera.org/specializations/machine-learning-introduction": [
        {"slug": "week-1", "title": "Week 1", "url": None},
        {"slug": "week-2", "title": "Week 2", "url": None},
        {"slug": "week-3", "title": "Week 3", "url": None},
        {"slug": "week-4", "title": "Week 4", "url": None},
        {"slug": "week-5", "title": "Week 5", "url": None},
        {"slug": "week-6", "title": "Week 6", "url": None},
    ],
    "https://coursera.org/learn/linear-algebra-machine-learning": [
        {"slug": "week-1", "title": "Week 1", "url": None},
        {"slug": "week-2", "title": "Week 2", "url": None},
        {"slug": "week-3", "title": "Week 3", "url": None},
        {"slug": "week-4", "title": "Week 4", "url": None},
        {"slug": "week-5", "title": "Week 5", "url": None},
    ],
}
```

Do not add Imperial as covered-by 3Blue1Brown.

- [ ] **Step 3: Compile and validate**

Run: `make validate`

Expected: `OK`; resource count **rises** by the number of new lesson URLs; featured count unchanged or nearly unchanged.

- [ ] **Step 4: Assert Focus on empty progress is 3Blue1Brown lesson 1**

```bash
python3 - <<'PY'
import json, sys
from pathlib import Path
sys.path.insert(0, "scripts")
from focus import next_focus
g=json.loads(Path("data/graph.json").read_text())
r=json.loads(Path("data/resources.json").read_text())
f=next_focus(g,r,{})
print(f)
assert f["part_id"] or f["resource_id"]
assert "linear" in (f.get("resource_title") or "").lower() or "essence" in (f.get("label") or "").lower()
PY
```

Expected: Focus label includes Essence of Linear Algebra and the first live lesson title.

- [ ] **Step 5: Commit**

```bash
git add scripts/outlines.py data/resources.json data/graph.json
git commit -m "$(cat <<'EOF'
Seed lesson outlines for the first Do courses a beginner actually opens.

EOF
)"
```

---

### Task 5: Server Focus endpoint and PUT rollup

**Files:**
- Modify: `scripts/serve.py`
- Create: `tests/test_serve_focus.py` (optional: call `focus.next_focus` with files on disk; do not bind port 7432 in unit tests)

**Interfaces:**
- Consumes: `GET /data/focus.json`; `PUT /data/progress.json` body still a dict of id→status.
- Produces: GET → JSON Focus object; PUT → `200` JSON `{progress, focus}` after `apply_status` **is not** replayed per key (client already applied). **Do** run a `rollup_all(progress, by_id)` that re-applies containment invariants before write (parent done ⇒ parts done; any part not done ⇒ parent not done; all parts done ⇒ parent done).

```python
def rollup_all(progress: dict, resources_by_id: dict) -> dict:
    out = dict(progress)
    for rec in resources_by_id.values():
        parts = rec.get("parts") or []
        if not parts:
            continue
        if out.get(rec["id"]) == "done":
            for p in parts:
                out[p["id"]] = "done"
        elif parts and all(out.get(p["id"]) == "done" for p in parts):
            out[rec["id"]] = "done"
        elif out.get(rec["id"]) == "done" and any(out.get(p["id"]) != "done" for p in parts):
            out[rec["id"]] = "doing"
    return out
```

Put `rollup_all` in `scripts/focus.py`. PUT handler:

```python
from focus import next_focus, rollup_all, by_id
# load resources.json + graph.json from DATA
progress = rollup_all(payload, by_id(resources))
PROGRESS.write_text(...)
body = json.dumps({"progress": progress, "focus": next_focus(graph, resources, progress)})
self.send_response(200)
self.send_header("Content-Type", "application/json")
self.send_header("Content-Length", str(len(body.encode())))
self.end_headers()
self.wfile.write(body.encode())
```

GET `/data/focus.json`:

```python
if self.path.rstrip("/") == "/data/focus.json":
    resources = json.loads((ROOT / "data" / "resources.json").read_text())
    graph = json.loads((ROOT / "data" / "graph.json").read_text())
    progress = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
    body = json.dumps(next_focus(graph, resources, progress))
    ...
    return
```

- [ ] **Step 1: Write `tests/test_focus.py` cases for `rollup_all`**

```python
class TestRollupAll(unittest.TestCase):
    def test_parent_done_fills_parts(self):
        from focus import rollup_all
        out = rollup_all({"r-fastai": "done"}, by_id(RES2))
        self.assertEqual(out["r-fastai:lesson2"], "done")
```

- [ ] **Step 2: Run to fail, then implement `rollup_all`**

Run: `python3 -m unittest tests.test_focus.TestRollupAll -v`

- [ ] **Step 3: Wire serve.py GET/PUT**

Keep `SimpleHTTPRequestHandler` GET for other paths. Intercept `/data/focus.json` **before** `super().do_GET()`.

- [ ] **Step 4: Restart atlas server and curl**

If LaunchAgent owns 7432:

```bash
launchctl kickstart -k gui/$(id -u)/com.sagar.ai-sme-map
curl -sS http://127.0.0.1:7432/data/focus.json | python3 -m json.tool
```

Expected: JSON with `done: false` and a `label`.

- [ ] **Step 5: Commit**

```bash
git add scripts/serve.py scripts/focus.py tests/test_focus.py
git commit -m "$(cat <<'EOF'
Serve Focus as JSON and keep parent/part progress consistent on save.

EOF
)"
```

---

### Task 6: UI Focus strip and nested lessons

**Files:**
- Modify: `web/index.html` (add `<section id="focus" class="focus">`)
- Modify: `web/app.js`
- Modify: `web/styles.css`

**Interfaces:**
- Consumes: `GET /data/focus.json`; resources `parts` / `parent_id`; PUT response `{progress, focus}` when present, else refetch focus.
- Produces: header Next = `focus.label`; Focus strip with Open + Mark done; drawer lesson rows; search badge `lesson of {parent}` and `covered by {parent}` when `isComplete` in JS.

JS completeness must match Python: parent done covers parts; all parts done covers parent. Port the 20-line `isComplete` / `applyStatus` into `web/app.js` (comment: keep in sync with `scripts/focus.py`). After click, `progress = applyStatus(...)`, PUT, use returned `focus` if `Content-Type` is JSON.

Mark done on the Focus strip sets `focus.part_id || focus.resource_id` to `done`.

```javascript
function renderFocus(focus) {
  const el = $("focus");
  if (focus.done) {
    el.innerHTML = `<p class="kicker">Focus</p><h2>Atlas complete for the beginner path</h2>`;
    return;
  }
  el.innerHTML = `
    <p class="kicker">Focus · ${focus.station_title}</p>
    <h2>${focus.label}</h2>
    <p><a href="${focus.url}" target="_blank" rel="noreferrer">Open</a>
    <button type="button" data-focus-done="${focus.part_id || focus.resource_id}">Mark done</button></p>`;
}
```

In `renderResource`, if `r.parent_id` and parent is complete, add `<span class="badge">covered by …</span>`.

In `renderResource` / new `renderParent(r, …)` for Do cards with `r.parts`, list parts with `statusButtons(part.id, …)`.

`paintCounts` Next cell: `focus.label` at the existing 16px size.

- [ ] **Step 1: Add `#focus` markup and CSS** (reuse ticket/paper tokens; no new palette)

```css
.focus {
  background: var(--ticket);
  border: 1px solid var(--ink);
  padding: 16px 20px;
  margin: 20px 0 8px;
}
.focus h2 { font-family: "Fraunces", serif; font-size: 28px; margin: 0 0 8px; }
```

- [ ] **Step 2: Wire load/redraw/click in `app.js`**

On `data-focus-done`, apply status, save, redraw.

- [ ] **Step 3: Hard-refresh http://127.0.0.1:7432**

Verify: Focus shows a lesson; Open hits the lesson URL when present (Ng week Open hits the specialization URL because `url` falls back to parent); Mark done advances the strip; station `nDone/nDo` still counts all Do ids; Imperial does not auto-complete after 3Blue1Brown.

- [ ] **Step 4: Commit**

```bash
git add web/index.html web/app.js web/styles.css
git commit -m "$(cat <<'EOF'
Show one next lesson on the atlas and let each part be ticked.

EOF
)"
```

---

### Task 7: Validate + README

**Files:**
- Modify: `README.md` (Focus + progress keys for `parent:slug`)
- Modify: `Makefile` if you add `test:`

```makefile
test:
	python3 -m unittest discover -s tests -v
validate: compile test
	python3 scripts/validate.py
```

- [ ] **Step 1: Run the proof commands**

```bash
cd /Users/sagar/dev/ai-sme-map
python3 -m unittest discover -s tests -v
make validate
curl -sS http://127.0.0.1:7432/data/focus.json
```

Expected: unittest OK; validate OK; focus JSON has `label`.

- [ ] **Step 2: README — one short paragraph**

Completing a **station** is still finishing its Do rail. **Focus** is the next lesson of the first Do item so a beginner always has one sitting. Child lessons are containment, not extra homework once the parent is done.

- [ ] **Step 3: Commit**

```bash
git add README.md Makefile
git commit -m "$(cat <<'EOF'
Document Focus versus station completion and run unit tests on validate.

EOF
)"
```

---

## Self-review

1. **Spec coverage:** picker (`station.do[0]`), containment rollup, optional URLs, no harvest explosion, no substitutes, UI Focus, GET/PUT, T0 seeds, tests — each has a task.
2. **Placeholders:** none; outline URLs that 404 are dropped in Task 4, not left TBD.
3. **Types:** `next_focus` → dict with `done` / `part_id`; `apply_status` → new progress dict; compile `attach_outlines(resources, outlines)`.
