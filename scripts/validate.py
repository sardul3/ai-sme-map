#!/usr/bin/env python3
"""Fail if the catalog is thin or graph rails dangle."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

sys.path.insert(0, str(Path(__file__).parent))
from commute import validate_commute  # noqa: E402

REQUIRED_BRANCHES = {
    "linear-algebra",
    "calculus",
    "probability",
    "classical-ml",
    "ai",
    "deep-learning",
    "computer-vision",
    "nlp",
    "generative",
    "rl",
    "mlsys",
    "theory",
    "optimization",
    "causal",
    "graphs",
    "speech",
    "robotics",
    "recommenders",
    "timeseries",
    "interpretability",
    "alignment",
    "scientific-ml",
    "privacy",
    "multimodal",
    "agents",
    "bandits",
    "diffusion",
    "ssm",
    "3d-vision",
    "fairness",
    "info-theory",
    "pgm",
    "eval",
    "data-centric",
    "compilers",
    "world-models",
    "code-llm",
    "imitation",
    "marl",
}

MIN_STATIONS = 40
RAILS = ("do", "parallel", "skim", "project")


def main() -> None:
    resources = json.loads((DATA / "resources.json").read_text())
    graph = json.loads((DATA / "graph.json").read_text())
    urls = [r["url"] for r in resources]
    ids = {r["id"] for r in resources}
    errors = []
    if len(resources) < 500:
        errors.append(f"need ≥500 resources, have {len(resources)}")
    if len(set(urls)) != len(urls):
        errors.append("duplicate URLs")
    if not all(u.startswith("http") for u in urls):
        errors.append("non-http URL")
    nodes = graph["nodes"]
    if len(nodes) < MIN_STATIONS:
        errors.append(f"need ≥{MIN_STATIONS} stations, have {len(nodes)}")
    branches = {n["branch"] for n in nodes}
    missing = sorted(REQUIRED_BRANCHES - branches)
    if missing:
        errors.append("missing branches: " + ", ".join(missing))
    for stage in range(8):
        staged = [n for n in nodes if n["stage"] == stage]
        if not staged:
            errors.append(f"empty stage T{stage}")
        rails = {n["rail"] for n in staged}
        if stage in (5, 7) and rails < {"theory", "practice"}:
            errors.append(f"T{stage} needs both theory and practice rails, has {sorted(rails)}")
    for node in nodes:
        for rail in RAILS:
            if not node.get(rail):
                errors.append(f"{node['id']} empty {rail}")
            for rid in node.get(rail, []):
                if rid not in ids:
                    errors.append(f"{node['id']} {rail} dangling {rid}")
    for r in resources:
        for p in r.get("parts") or []:
            pid = p.get("id")
            if not pid:
                errors.append(f"{r['id']} part missing id")
                continue
            if pid not in ids and not str(pid).startswith(r["id"] + ":"):
                errors.append(f"{r['id']} bad part id {pid}")
            if p.get("url") and p["url"] not in set(urls):
                errors.append(f"{r['id']} part missing catalog url {p['url']}")
            if pid == r["id"]:
                errors.append(f"{r['id']} part id equals parent")
    resources_by_id = {r["id"]: r for r in resources}
    primaries = []
    for node in nodes:
        for rid in node.get("do") or []:
            if rid not in primaries:
                primaries.append(rid)
            if len(primaries) == 10:
                break
        if len(primaries) == 10:
            break
    missing_sit = [
        resources_by_id[i]["title"]
        for i in primaries
        if i in resources_by_id and not resources_by_id[i].get("sitting")
    ]
    if missing_sit:
        errors.append("T0-T1 first Do items missing sitting: " + ", ".join(missing_sit))
    errors.extend(validate_commute(resources, nodes))
    if errors:
        print("FAIL")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    featured = sum(1 for r in resources if r.get("featured"))
    print(f"OK {len(resources)} resources, {featured} featured, {len(graph['nodes'])} stations")


if __name__ == "__main__":
    main()
