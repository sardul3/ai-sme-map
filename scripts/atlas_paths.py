"""Site-root paths so localhost and project GitHub Pages share one data/ prefix."""

from __future__ import annotations

PAGE_STEMS = frozenset({"index", "commute", "library"})


def atlas_root(pathname: str) -> str:
    """Directory that contains data/ for a browser request path."""
    path = pathname or "/"
    if not path.startswith("/"):
        path = "/" + path
    trimmed = path.rstrip("/")
    last = trimmed.rsplit("/", 1)[-1]
    stem = last[:-5] if last.endswith(".html") else last
    if last.endswith(".html") or stem in PAGE_STEMS:
        trimmed = trimmed.rsplit("/", 1)[0]
    if trimmed.endswith("/web"):
        trimmed = trimmed[: -len("/web")]
    elif trimmed == "web":
        trimmed = ""
    if not trimmed or trimmed == "/":
        return "/"
    return trimmed + "/"
