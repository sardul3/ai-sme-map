#!/usr/bin/env python3
"""Show harvest files whose SHA-256 drifted from the last compile pin."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARVEST = ROOT / "harvest"
PIN = ROOT / "data" / "harvest.hashes.json"


def main() -> None:
    if not PIN.exists():
        print("no pin; run make compile first")
        sys.exit(1)
    pinned = json.loads(PIN.read_text())
    now = {}
    for path in sorted(HARVEST.glob("*.md")):
        now[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    added = sorted(set(now) - set(pinned))
    removed = sorted(set(pinned) - set(now))
    changed = sorted(k for k in now if k in pinned and now[k] != pinned[k])
    if not added and not removed and not changed:
        print("harvest unchanged since last compile")
        return
    print("Do-rail edits require a human. Harvest diffs belong on Skim unless ranked.")
    for name in added:
        print(f"  added   {name}")
    for name in removed:
        print(f"  removed {name}")
    for name in changed:
        print(f"  changed {name}")
    sys.exit(2)


if __name__ == "__main__":
    main()
