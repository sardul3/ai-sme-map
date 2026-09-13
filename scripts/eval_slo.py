#!/usr/bin/env python3
"""Local map-quality SLO. Opt-in eval log; Do-rail 404s fail."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
sys.path.insert(0, str(ROOT / "scripts"))
from check_links import classify  # noqa: E402


def time_to_first_done_ms(events: list[dict]) -> int | None:
    load = next((e.get("t") for e in events if e.get("event") == "load"), None)
    done = next(
        (
            e.get("t")
            for e in events
            if e.get("event") == "keyboard_done"
            or (e.get("event") == "focus_status" and e.get("st") == "done")
        ),
        None,
    )
    if load is None or done is None:
        return None
    return int(done) - int(load)


def do_rail_slo_ok(status: dict) -> bool:
    for row in (status.get("urls") or {}).values():
        if classify(row.get("error")) == "fail":
            return False
    return True


def main() -> None:
    eval_path = DATA / "eval_log.json"
    if eval_path.exists():
        events = json.loads(eval_path.read_text())
        if not isinstance(events, list):
            raise SystemExit("eval_log.json must be an array")
        ttfd = time_to_first_done_ms(events)
        print("events", len(events))
        print("time_to_first_done_ms", ttfd)
    else:
        print("no data/eval_log.json (paste localStorage.atlas_eval_log here, opt-in)")

    status_path = DATA / "link_status.json"
    if status_path.exists():
        status = json.loads(status_path.read_text())
        ok = do_rail_slo_ok(status)
        print("do_rail_404_slo", "PASS" if ok else "FAIL")
        if not ok:
            raise SystemExit(1)
    else:
        print("no data/link_status.json; run make links-do")


if __name__ == "__main__":
    main()
