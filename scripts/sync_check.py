#!/usr/bin/env python3
"""Confirm the Syncthing/iCloud unit is a schema-versioned progress file (E12)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRESS = ROOT / "data" / "progress.json"


def main() -> None:
    if not PROGRESS.exists():
        PROGRESS.write_text(json.dumps({"schema_version": 1}, indent=2) + "\n")
    payload = json.loads(PROGRESS.read_text())
    if not isinstance(payload, dict) or "schema_version" not in payload:
        raise SystemExit("progress.json must include schema_version; see docs/SYNC.md")
    print("sync unit OK:", PROGRESS, "schema_version", payload["schema_version"])


if __name__ == "__main__":
    main()
