"""Beginner Focus: next sitting is the first unfinished part of station.do[0].

Keep in sync with web/app.js nextFocus.
"""

from __future__ import annotations

STATUS = ("todo", "doing", "skimmed", "done")


def by_id(resources: list[dict]) -> dict[str, dict]:
    return {r["id"]: r for r in resources}


def parent_of(resource_id: str, resources_by_id: dict) -> dict | None:
    rec = resources_by_id.get(resource_id)
    if rec and rec.get("parent_id"):
        return resources_by_id.get(rec["parent_id"])
    for r in resources_by_id.values():
        for p in r.get("parts") or []:
            if p["id"] == resource_id:
                return r
    return None


def is_complete(progress: dict, resource_id: str, resources_by_id: dict) -> bool:
    if progress.get(resource_id) == "done":
        return True
    rec = resources_by_id.get(resource_id) or {}
    parts = rec.get("parts") or []
    if parts and all(is_complete(progress, p["id"], resources_by_id) for p in parts):
        return True
    parent = parent_of(resource_id, resources_by_id)
    if parent and progress.get(parent["id"]) == "done":
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
        parent = parent_of(resource_id, resources_by_id)
        if parent:
            parent_parts = parent.get("parts") or []
            if parent_parts and all(out.get(p["id"]) == "done" for p in parent_parts):
                out[parent["id"]] = "done"
    else:
        parent = parent_of(resource_id, resources_by_id)
        if parent and out.get(parent["id"]) == "done":
            out[parent["id"]] = "doing"
    return out


def rollup_all(progress: dict, resources_by_id: dict) -> dict:
    out = dict(progress)
    for rec in resources_by_id.values():
        parts = rec.get("parts") or []
        if not parts:
            continue
        if out.get(rec["id"]) == "done":
            for p in parts:
                out[p["id"]] = "done"
        elif all(out.get(p["id"]) == "done" for p in parts):
            out[rec["id"]] = "done"
        elif out.get(rec["id"]) == "done":
            out[rec["id"]] = "doing"
    return out


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
        "sitting": rec.get("sitting") or "",
        "label": label,
    }


def next_focus(graph: dict, resources: list[dict], progress: dict) -> dict:
    resources_by_id = by_id(resources)
    for station in graph.get("nodes") or []:
        do = station.get("do") or []
        if not do:
            continue
        primary_id = do[0]
        rec = resources_by_id.get(primary_id)
        if not rec:
            continue
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
