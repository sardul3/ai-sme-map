#!/usr/bin/env python3
"""Fail CI only on 404/410 for Do-rail (and featured unless --do-only). Warn on flaky network."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
STATUS_PATH = DATA / "link_status.json"
UA = {"User-Agent": "ai-sme-map-linkcheck"}


def classify(err: str | None) -> str:
    if err is None:
        return "ok"
    token = err.strip()
    if token in {"404", "410"} or token.endswith(" 404") or token.endswith(" 410"):
        return "fail"
    return "warn"


def is_stale(last_ok: str | None, days: int = 90, now: datetime | None = None) -> bool:
    if not last_ok:
        return False
    now = now or datetime.now(timezone.utc)
    try:
        ts = datetime.strptime(last_ok, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    return (now - ts).days > days


def check(url: str, timeout: int = 12) -> str | None:
    audio = url.lower().split("?", 1)[0].endswith((".mp3", ".m4a", ".aac", ".ogg", ".oga", ".opus"))
    methods = ("HEAD",) if audio else ("HEAD", "GET")
    for method in methods:
        try:
            headers = dict(UA)
            if method == "GET" and audio:
                headers["Range"] = "bytes=0-0"
            req = Request(url, method=method, headers=headers)
            with urlopen(req, timeout=timeout) as resp:
                if resp.status in (404, 410):
                    return f"{resp.status}"
                return None
        except HTTPError as e:
            if e.code in (404, 410):
                return f"{e.code}"
            if e.code == 416 and audio:
                return None
            if method == methods[-1]:
                return f"HTTP {e.code}"
        except (URLError, TimeoutError, OSError) as e:
            if method == methods[-1]:
                return type(e).__name__
    return "unreachable"


def commute_urls(resources: list[dict]) -> list[str]:
    urls = []
    for rec in resources:
        if not rec.get("audio_url"):
            continue
        if rec.get("url"):
            urls.append(rec["url"])
        urls.append(rec["audio_url"])
    return urls


def collect_urls(do_only: bool) -> list[str]:
    resources = json.loads((DATA / "resources.json").read_text())
    graph = json.loads((DATA / "graph.json").read_text())
    by_id = {r["id"]: r for r in resources}
    urls = []
    for n in graph["nodes"]:
        for rid in n.get("do") or []:
            rec = by_id.get(rid)
            if rec:
                urls.append(rec["url"])
            for p in (rec or {}).get("parts") or []:
                if p.get("url"):
                    urls.append(p["url"])
    if not do_only:
        for r in resources:
            if r.get("featured"):
                urls.append(r["url"])
        urls.extend(commute_urls(resources))
    seen = []
    for u in urls:
        if u not in seen:
            seen.append(u)
    return seen


def write_status(rows: dict[str, dict]) -> None:
    prev = {}
    if STATUS_PATH.exists():
        try:
            prev = json.loads(STATUS_PATH.read_text()).get("urls") or {}
        except json.JSONDecodeError:
            prev = {}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = {}
    for url, row in rows.items():
        last_ok = prev.get(url, {}).get("last_ok")
        if row.get("ok"):
            last_ok = now
        out[url] = {**row, "last_ok": last_ok}
    STATUS_PATH.write_text(
        json.dumps({"checked_at": now, "urls": out}, indent=2) + "\n"
    )


def main() -> None:
    do_only = "--do-only" in sys.argv
    seen = collect_urls(do_only)
    fails = []
    warns = []
    rows = {}
    for u in seen:
        err = check(u)
        kind = classify(err)
        rows[u] = {"ok": kind == "ok", "error": err}
        if kind == "fail":
            fails.append(f"{err} {u}")
            print("FAIL", err, u)
        elif kind == "warn":
            warns.append(f"{err} {u}")
            print("WARN", err, u)
        else:
            print("OK", u)
    write_status(rows)
    if warns:
        print(f"\n{len(warns)} flaky or blocked URLs (not CI-fail)")
    if fails:
        print(f"\n{len(fails)} dead URLs (404/410)")
        sys.exit(1)
    print(f"OK {len(seen)} URLs ({len(warns)} warnings)")


if __name__ == "__main__":
    main()
