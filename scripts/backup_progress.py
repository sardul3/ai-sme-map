#!/usr/bin/env python3
"""Copy progress.json to data/backups/ with a timestamp."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "progress.json"
DEST = ROOT / "data" / "backups"


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    if not SRC.exists():
        print("no progress.json")
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = DEST / f"progress-{stamp}.json"
    shutil.copy2(SRC, out)
    print(out)


if __name__ == "__main__":
    main()
