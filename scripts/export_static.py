#!/usr/bin/env python3
"""Copy web + catalog JSON into a flat dist/ for GitHub Pages (no PUT, empty progress)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"

WEB_FILES = ("index.html", "commute.html", "app.js", "styles.css")
DATA_FILES = (
    "graph.json",
    "resources.json",
    "catalog_meta.json",
    "placement.json",
    "link_status.json",
    "feed.xml",
)


def export_static(dest: Path | None = None) -> Path:
    dest = dest or DIST
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "data").mkdir(parents=True)
    for name in WEB_FILES:
        shutil.copy2(ROOT / "web" / name, dest / name)
    for name in DATA_FILES:
        src = ROOT / "data" / name
        if src.exists():
            shutil.copy2(src, dest / "data" / name)
    (dest / "data" / "progress.json").write_text(
        json.dumps({"schema_version": 1}, indent=2) + "\n"
    )
    (dest / ".nojekyll").write_text("")
    print(dest, "— flat static site; progress is localStorage (PUT is not shipped)")
    return dest


def main() -> None:
    export_static()


if __name__ == "__main__":
    main()
