"""Topic request: match the shelf, else propose one GitHub awesome-* README.

Does not edit ranked Tonight stations or commute EPISODES. A new harvest file
compiles onto Library · unassigned. Human gate before any Do-rail change.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
HARVEST = ROOT / "harvest"
DATA = ROOT / "data"
SOURCES = HARVEST / "SOURCES.md"
GITHUB_API = "https://api.github.com/search/repositories"
UA = "SME-Atlas/1.0 (topic-request; personal catalog)"
RESOURCE_CAP = 12

BANNED_HOSTS = (
    "youtube.com",
    "youtu.be",
    "coursera.org",
)


def normalize_topic(raw: str) -> str:
    text = (raw or "").strip().lower()
    text = re.sub(r"[,:;]+$", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_topic(raw: str) -> str:
    text = (raw or "").strip()
    m = re.match(r"(?i)^topic:\s*(.+)$", text)
    if m:
        text = m.group(1)
    return normalize_topic(text)


def _slug(topic: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", normalize_topic(topic))
    return slug.strip("-") or "topic"


def harvest_filename(topic: str) -> str:
    return f"topic-{_slug(topic)}.md"


def github_awesome_query(topic: str) -> str:
    return f"awesome {normalize_topic(topic)} in:name"


def _blob(*parts: object) -> str:
    return " ".join(str(p or "") for p in parts).lower()


def _contains(needle: str, *parts: object) -> bool:
    hay = _blob(*parts)
    if not needle:
        return False
    if needle in hay:
        return True
    tokens = [t for t in re.split(r"[^a-z0-9]+", hay) if t]
    return needle in tokens or all(tok in tokens for tok in needle.split() if tok)


def _harvest_rows(harvest_files: list) -> list[dict]:
    rows = []
    for item in harvest_files:
        if isinstance(item, str):
            rows.append({"name": item, "role": ""})
        else:
            rows.append({"name": item.get("name") or "", "role": item.get("role") or ""})
    return rows


def match_shelf(topic: str, harvest_files, stations, resources) -> dict:
    needle = normalize_topic(topic)
    harvest_hits = []
    harvest_names = set()
    for row in _harvest_rows(harvest_files):
        name = row["name"]
        if _contains(needle, name, row["role"], Path(name).stem.replace("-", " ")):
            harvest_hits.append({"name": name, "role": row["role"]})
            harvest_names.add(name)
    station_hits = []
    for st in stations or []:
        if _contains(needle, st.get("id"), st.get("title"), st.get("branch"), st.get("why")):
            station_hits.append(
                {
                    "id": st.get("id"),
                    "title": st.get("title"),
                    "branch": st.get("branch"),
                    "why": st.get("why"),
                }
            )
    featured_hits = []
    leftover = []
    for rec in resources or []:
        if not _contains(
            needle,
            rec.get("title"),
            rec.get("evidence"),
            " ".join(rec.get("branches") or []),
        ):
            continue
        source = rec.get("source") or ""
        if source in harvest_names:
            continue
        card = {
            "id": rec.get("id"),
            "title": rec.get("title"),
            "url": rec.get("url"),
            "source": source,
            "featured": bool(rec.get("featured")),
        }
        if rec.get("featured") and source == "curated":
            featured_hits.append(card)
        else:
            leftover.append(card)
    return {
        "harvest": harvest_hits,
        "stations": station_hits,
        "featured": featured_hits,
        "resources": leftover[:RESOURCE_CAP],
    }


def shelf_has_hits(hits: dict) -> bool:
    return any(hits.get(k) for k in ("harvest", "stations", "featured", "resources"))


def is_allowed_harvest_url(url: str) -> bool:
    raw = (url or "").strip()
    if not raw:
        return False
    parsed = urlparse(raw)
    host = parsed.netloc.lower().lstrip("www.")
    path = parsed.path.lower()
    if any(bad in host or bad in raw.lower() for bad in BANNED_HOSTS):
        return False
    if host == "raw.githubusercontent.com":
        parts = [p for p in path.split("/") if p]
        return len(parts) >= 2 and "awesome-" in parts[1] and path.endswith("readme.md")
    if host == "github.com":
        parts = [p for p in path.split("/") if p]
        return len(parts) >= 2 and parts[1].startswith("awesome-")
    return False


def issue_comment_body(*, hits=None, scrape_pr: str | None = None, none: bool = False) -> str:
    if hits and shelf_has_hits(hits):
        lines = ["Already on the shelf.", ""]
        if hits.get("harvest"):
            lines.append("Harvest lists:")
            for row in hits["harvest"]:
                role = f" — {row['role']}" if row.get("role") else ""
                lines.append(f"- `{row['name']}`{role}")
            lines.append("")
        if hits.get("stations"):
            lines.append("Stations:")
            for st in hits["stations"]:
                lines.append(f"- {st.get('title')} (`{st.get('id')}`)")
            lines.append("")
        if hits.get("featured"):
            lines.append("Featured:")
            for rec in hits["featured"]:
                lines.append(f"- {rec.get('title')}")
        return "\n".join(lines).strip() + "\n"
    if scrape_pr:
        return (
            f"Opened a harvest PR: {scrape_pr}\n\n"
            "New markdown compiles onto Library · unassigned. "
            "Human gate: do not merge Do rail edits or commute rank rows.\n"
        )
    if none:
        return (
            "No awesome-* README matched this topic. Stop — "
            "add a GitHub awesome list URL in a comment if you have one.\n"
        )
    return "No action taken.\n"


def load_sources_table(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        m = re.match(r"^\|\s*([A-Za-z0-9._-]+\.md)\s*\|\s*([^|]+)\|", line)
        if not m:
            continue
        rows.append({"name": m.group(1).strip(), "role": m.group(2).strip()})
    return rows


def harvest_files_from_disk(harvest_dir: Path | None = None, sources_path: Path | None = None) -> list[dict]:
    roles = {}
    src = sources_path or SOURCES
    if src.exists():
        for row in load_sources_table(src.read_text()):
            roles[row["name"]] = row["role"]
    folder = harvest_dir or HARVEST
    files = []
    if folder.exists():
        for path in sorted(folder.glob("*.md")):
            if path.name == "SOURCES.md":
                continue
            files.append({"name": path.name, "role": roles.get(path.name, "")})
    return files


def fetch_text(url: str, timeout: int = 45) -> str:
    headers = {"User-Agent": UA}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout) as res:
        return res.read().decode("utf-8", errors="replace")


def raw_readme_url(html_url: str, default_branch: str = "master") -> str:
    parsed = urlparse(html_url)
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        return ""
    owner, repo = parts[0], parts[1]
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{default_branch}/README.md"


def pick_awesome_repo(items: list[dict], topic: str) -> dict | None:
    needle = normalize_topic(topic)
    for item in items:
        name = (item.get("name") or "").lower()
        html = item.get("html_url") or ""
        if not name.startswith("awesome-"):
            continue
        if needle and needle not in name.replace("-", " ") and needle not in name:
            continue
        if not is_allowed_harvest_url(html):
            continue
        return item
    return None


def search_awesome_lists(topic: str, opener=None) -> list[dict]:
    query = github_awesome_query(topic)
    url = f"{GITHUB_API}?q={quote_plus(query)}&per_page=5"
    fetch = opener or fetch_text
    body = fetch(url)
    data = json.loads(body)
    return data.get("items") or []


def write_topic_harvest(topic: str, markdown: str, dest_dir: Path | None = None) -> Path:
    folder = dest_dir or HARVEST
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / harvest_filename(topic)
    text = markdown if markdown.endswith("\n") else markdown + "\n"
    path.write_text(text)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Match a topic to the shelf or fetch one awesome list.")
    parser.add_argument("--topic", default="")
    parser.add_argument("--issue-title", default="")
    parser.add_argument("--issue", action="store_true")
    parser.add_argument("--comment-path", type=Path)
    parser.add_argument("--wrote-path", type=Path)
    args = parser.parse_args(argv)

    topic = parse_topic(args.topic or args.issue_title)
    if not topic:
        sys.stderr.write("topic-request: empty topic\n")
        return 2

    stations = []
    resources = []
    graph_path = DATA / "graph.json"
    res_path = DATA / "resources.json"
    if graph_path.exists():
        stations = json.loads(graph_path.read_text()).get("nodes") or []
    if res_path.exists():
        resources = json.loads(res_path.read_text())

    hits = match_shelf(topic, harvest_files_from_disk(), stations, resources)
    comment = ""
    wrote = ""
    if shelf_has_hits(hits):
        comment = issue_comment_body(hits=hits)
    else:
        try:
            items = search_awesome_lists(topic)
            picked = pick_awesome_repo(items, topic)
        except Exception as exc:
            sys.stderr.write(f"topic-request search failed: {exc}\n")
            picked = None
        if not picked:
            comment = issue_comment_body(none=True)
        else:
            branch = picked.get("default_branch") or "master"
            raw = raw_readme_url(picked["html_url"], branch)
            if not is_allowed_harvest_url(raw):
                comment = issue_comment_body(none=True)
            else:
                try:
                    body = fetch_text(raw)
                except Exception as exc:
                    sys.stderr.write(f"topic-request fetch failed: {exc}\n")
                    comment = issue_comment_body(none=True)
                else:
                    if len(body) < 200:
                        comment = issue_comment_body(none=True)
                    else:
                        path = write_topic_harvest(topic, body)
                        wrote = str(path.relative_to(ROOT))
                        comment = (
                            f"Fetched `{picked.get('full_name')}` into `{wrote}`.\n"
                            "Open a harvest PR. Human gate: Library · unassigned only; "
                            "do not edit the Do rail or commute ranks.\n"
                        )

    if args.comment_path:
        args.comment_path.write_text(comment)
    else:
        sys.stdout.write(comment)
    if args.wrote_path:
        args.wrote_path.write_text(wrote + ("\n" if wrote else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
