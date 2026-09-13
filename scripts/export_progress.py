#!/usr/bin/env python3
"""Export progress.json to stdout or a path. Does not include secrets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "data" / "progress.json"


def main() -> None:
    data = json.loads(SRC.read_text()) if SRC.exists() else {"schema_version": 1}
    out = sys.argv[1] if len(sys.argv) > 1 else None
    text = json.dumps(data, indent=2) + "\n"
    if out:
        Path(out).write_text(text)
        print(out)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
