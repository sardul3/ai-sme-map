"""Resources that are cataloged but sit on neither Tonight nor Commute."""

from __future__ import annotations

RAILS = ("do", "parallel", "skim", "project")


def assigned_ids(resources: list[dict], graph: dict) -> set[str]:
    by_id = {r["id"]: r for r in resources if r.get("id")}
    ids: set[str] = set()
    for node in graph.get("nodes") or []:
        for rail in RAILS:
            ids.update(node.get(rail) or [])
    for rid in list(ids):
        for part in (by_id.get(rid) or {}).get("parts") or []:
            if part.get("id"):
                ids.add(part["id"])
    for rec in resources:
        rid = rec.get("id")
        if not rid:
            continue
        if rec.get("parent_id") and rec["parent_id"] in ids:
            ids.add(rid)
        if rec.get("audio_url") and rec.get("purpose"):
            ids.add(rid)
    return ids


def unassigned(resources: list[dict], graph: dict) -> list[dict]:
    have = assigned_ids(resources, graph)
    return [r for r in resources if r.get("id") and r["id"] not in have]


def category_of(row: dict) -> str:
    src = row.get("source") or ""
    if src.endswith(".md"):
        return f"Harvest · {src.removesuffix('.md')}"
    if src == "curated" and row.get("featured"):
        return "Curated · featured"
    if src == "curated":
        return f"Curated · {row.get('kind') or 'other'}"
    if src == "commute":
        return "Commute inbox"
    return f"Other · {row.get('kind') or 'other'}"


def grouped(rows: list[dict]) -> list[dict]:
    buckets: dict[str, list[dict]] = {}
    for row in rows:
        buckets.setdefault(category_of(row), []).append(row)

    def sort_key(name: str) -> tuple[int, str]:
        if name == "Curated · featured":
            return (0, name)
        if name.startswith("Curated"):
            return (1, name)
        if name.startswith("Harvest"):
            return (2, name)
        return (3, name)

    out = []
    for name in sorted(buckets, key=sort_key):
        out.append(
            {
                "category": name,
                "rows": sorted(buckets[name], key=lambda r: (r.get("title") or "").lower()),
            }
        )
    return out
