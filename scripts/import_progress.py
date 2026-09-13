#!/usr/bin/env python3
"""Import a progress JSON after backing up the current file."""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "progress.json"
BACK = ROOT / "data" / "backups"


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: import_progress.py path.json")
    incoming = json.loads(Path(sys.argv[1]).read_text())
    if not isinstance(incoming, dict):
        raise SystemExit("object required")
    incoming.setdefault("schema_version", 1)
    BACK.mkdir(parents=True, exist_ok=True)
    if SRC.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        shutil.copy2(SRC, BACK / f"progress-before-import-{stamp}.json")
    SRC.write_text(json.dumps(incoming, indent=2) + "\n")
    print("imported", SRC)


if __name__ == "__main__":
    main()
