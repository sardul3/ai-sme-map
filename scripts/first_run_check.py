#!/usr/bin/env python3
"""Assert empty-progress Focus is the first 3Blue1Brown lesson (E4 first-run)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from focus import next_focus


def main() -> None:
    graph = json.loads((ROOT / "data" / "graph.json").read_text())
    resources = json.loads((ROOT / "data" / "resources.json").read_text())
    f = next_focus(graph, resources, {})
    if f.get("done"):
        raise SystemExit("empty progress should not be atlas-complete")
    label = f.get("label") or ""
    if "Essence of Linear Algebra" not in label:
        raise SystemExit(f"unexpected focus: {label}")
    if f.get("part_title") and f["part_title"] != "Vectors":
        raise SystemExit(f"expected Vectors, got {f.get('part_title')}")
    print("first-run OK:", label)


if __name__ == "__main__":
    main()
