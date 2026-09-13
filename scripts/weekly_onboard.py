"""Weekly scrape: refresh harvest lists and propose commute enclosures.

Does not edit ranked Tonight stations or commute EPISODES. New harvest URLs
compile onto Library · unassigned. New audio sits in data/inbox.json until a
human copies an original enclosure into scripts/commute.py.
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
HARVEST = ROOT / "harvest"
DATA = ROOT / "data"
INBOX = DATA / "inbox.json"

HARVEST_REMOTES = {
    "awesome-ml.md": "https://raw.githubusercontent.com/josephmisiti/awesome-machine-learning/master/README.md",
    "awesome-dl.md": "https://raw.githubusercontent.com/ChristosChristofidis/awesome-deep-learning/master/README.md",
    "awesome-nlp.md": "https://raw.githubusercontent.com/keon/awesome-nlp/master/README.md",
    "awesome-rl.md": "https://raw.githubusercontent.com/aikorea/awesome-rl/master/README.md",
    "awesome-cv.md": "https://raw.githubusercontent.com/jbhuang0604/awesome-computer-vision/master/README.md",
    "ml-youtube-courses.md": "https://raw.githubusercontent.com/dair-ai/ml-youtube-courses/main/README.md",
    "dl-papers-roadmap.md": "https://raw.githubusercontent.com/floodsung/Deep-Learning-Papers-Reading-Roadmap/master/README.md",
    "graph-dl.md": "https://raw.githubusercontent.com/naganandy/graph-based-deep-learning-literature/master/README.md",
    "have-fun-ml.md": "https://raw.githubusercontent.com/humphd/have-fun-with-machine-learning/master/README.md",
    "books.md": "https://raw.githubusercontent.com/josephmisiti/awesome-machine-learning/master/books.md",
}

COMMUTE_FEEDS = {
    "talking-machines": "https://feeds.acast.com/public/shows/talking-machines",
    "dataskeptic": "https://dataskeptic.libsyn.com/rss",
    "practical-ai": "https://changelog.com/practicalai/feed",
    "twiml": "https://twimlai.com/feed/",
    "latent-space": "https://api.substack.com/feed/podcast/1084089.rss",
    "ocdevel": "https://feeds.libsyn.com/53208/rss",
    "learning-machines-101": "https://learningmachines101.libsyn.com/rss",
}

UA = "SME-Atlas/1.0 (weekly-onboard; personal catalog)"
ITUNES = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}


def fetch_text(url: str, timeout: int = 45) -> str:
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=timeout) as res:
        return res.read().decode("utf-8", errors="replace")


def write_harvest_file(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body if body.endswith("\n") else body + "\n")


def known_episode_keys(episodes: list[dict]) -> set[str]:
    keys: set[str] = set()
    for ep in episodes:
        for field in ("url", "audio_url"):
            val = (ep.get(field) or "").strip().lower()
            if val:
                keys.add(val)
    return keys


def _sitting_min(item: ET.Element) -> int | None:
    el = item.find("itunes:duration", ITUNES)
    text = (el.text or "").strip() if el is not None else ""
    if not text:
        return None
    parts = text.split(":")
    try:
        if len(parts) == 3:
            h, m, s = [int(float(x)) for x in parts]
            return int(h * 60 + m + s / 60)
        if len(parts) == 2:
            m, s = [int(float(x)) for x in parts]
            return int(m + s / 60)
        n = float(text)
        return int(n / 60) if n > 200 else int(n)
    except ValueError:
        return None


def parse_feed_items(xml_text: str, provider: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    rows = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        page = (item.findtext("link") or "").strip()
        enc = item.find("enclosure")
        audio = (enc.get("url") if enc is not None else "") or ""
        audio = re.sub(r"[?].*$", "", audio)
        for prefix in (
            "https://pscrb.fm/rss/p/mgln.ai/e/35/",
            "https://pscrb.fm/rss/p/dts.podtrac.com/redirect.mp3/",
            "https://chrt.fm/track/",
        ):
            if audio.startswith(prefix):
                rest = audio[len(prefix) :]
                audio = rest if rest.startswith("http") else "https://" + rest
        rows.append(
            {
                "title": title,
                "url": page,
                "audio_url": audio,
                "sitting_min": _sitting_min(item),
                "provider": provider,
            }
        )
    return rows


def commute_candidates(items: list[dict], known: set[str]) -> list[dict]:
    out = []
    for item in items:
        title = item.get("title") or "(untitled)"
        audio = (item.get("audio_url") or "").strip()
        page = (item.get("url") or "").strip()
        sitting = item.get("sitting_min")
        blob = f"{audio} {page}".lower()
        if "youtube.com" in blob or "youtu.be" in blob:
            continue
        if not audio:
            continue
        path = urlparse(audio).path.lower()
        if not path.endswith((".mp3", ".m4a", ".aac", ".ogg", ".oga", ".opus")):
            continue
        if sitting is None or not (12 <= sitting <= 75):
            continue
        if page.lower() in known or audio.lower() in known:
            continue
        out.append(
            {
                "title": title,
                "url": page,
                "audio_url": audio,
                "sitting_min": sitting,
                "provider": item.get("provider") or "",
            }
        )
    return out


def merge_inbox(harvested: list[str], commute_new: list[dict], fetched_at: str) -> dict:
    return {
        "fetched_at": fetched_at,
        "human_gate": True,
        "note": "Harvest URLs compile to Library · unassigned. Copy commute candidates into scripts/commute.py by purpose/rank. Never auto-edit Do rails.",
        "harvested": harvested,
        "commute_candidates": commute_new,
    }


def refresh_harvest() -> list[str]:
    changed = []
    for name, url in HARVEST_REMOTES.items():
        dest = HARVEST / name
        try:
            body = fetch_text(url)
        except Exception as exc:
            print(f"harvest skip {name}: {exc}", file=sys.stderr)
            continue
        if len(body) < 200:
            print(f"harvest skip {name}: body too small", file=sys.stderr)
            continue
        prev = dest.read_text() if dest.exists() else ""
        write_harvest_file(dest, body)
        if dest.read_text() != prev:
            changed.append(name)
            print(f"harvest updated {name}")
        else:
            print(f"harvest unchanged {name}")
    return changed


def refresh_commute_inbox() -> list[dict]:
    sys.path.insert(0, str(Path(__file__).parent))
    from commute import EPISODES

    known = known_episode_keys(EPISODES)
    found: list[dict] = []
    for provider, url in COMMUTE_FEEDS.items():
        try:
            xml = fetch_text(url)
            items = parse_feed_items(xml, provider)
        except Exception as exc:
            print(f"feed skip {provider}: {exc}", file=sys.stderr)
            continue
        new = commute_candidates(items, known)
        print(f"feed {provider}: {len(items)} items, {len(new)} new")
        found.extend(new)
    # de-dupe by audio
    seen: set[str] = set()
    unique = []
    for row in found:
        key = row["audio_url"].lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    harvested = refresh_harvest()
    commute_new = refresh_commute_inbox()
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    blob = merge_inbox(harvested, commute_new, fetched_at)
    INBOX.write_text(json.dumps(blob, indent=2) + "\n")
    print(f"inbox {INBOX} harvest={len(harvested)} commute_new={len(commute_new)}")


if __name__ == "__main__":
    main()
