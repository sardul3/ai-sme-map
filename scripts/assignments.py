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


def filter_placements(placements: dict, known_ids: set[str]) -> dict:
    return {k: v for k, v in (placements or {}).items() if k in known_ids}


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
        if val is None:
            strip(rid)
            continue
        if not isinstance(val, dict):
            continue
        station = by_id.get(val.get("station"))
        rail = val.get("rail")
        if station is None or rail not in RAILS:
            continue
        strip(rid)
        if rid not in station[rail]:
            station[rail].append(rid)
    return out
