#!/usr/bin/env python3
"""Always-on atlas server: static files + loopback progress writes."""

from __future__ import annotations

import json
import subprocess
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PORT = 7432
HOST = "127.0.0.1"
LOOPBACK = {"127.0.0.1", "::1", "localhost"}

import sys

sys.path.insert(0, str(ROOT / "scripts"))
from assignments import apply_placements, filter_placements, validate_assignments  # noqa: E402
from focus import by_id, next_focus, rollup_all  # noqa: E402

PROGRESS = ROOT / "data" / "progress.json"
ASSIGNMENTS = ROOT / "data" / "assignments.json"
LAYOUT = ROOT / "data" / "roadmap_layout.json"
SEED = ROOT / "data" / "graph.seed.json"
PUT_PATHS = {
    "/data/progress.json",
    "/data/assignments.json",
    "/data/roadmap_layout.json",
}

PUBLIC_ALIASES = {
    "/": "/web/index.html",
    "/index.html": "/web/index.html",
    "/commute": "/web/commute.html",
    "/commute.html": "/web/commute.html",
    "/library": "/web/library.html",
    "/library.html": "/web/library.html",
    "/roadmap": "/web/roadmap.html",
    "/roadmap.html": "/web/roadmap.html",
    "/styles.css": "/web/styles.css",
    "/app.js": "/web/app.js",
    "/roadmap.js": "/web/roadmap.js",
}


def resolve_public_path(path: str) -> str:
    """Map pretty/root URLs onto files under web/."""
    if path == "/index.html":
        return PUBLIC_ALIASES["/index.html"]
    clean = path.rstrip("/") or "/"
    return PUBLIC_ALIASES.get(clean, path)


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def git_sha() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=ROOT,
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            or "uncommitted"
        )
    except Exception:
        return "uncommitted"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _json(self, code: int, payload) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        resolved = resolve_public_path(path)
        if resolved != path:
            self.path = resolved
            return super().do_GET()
        path = path.rstrip("/") or "/"
        if path == "/data/focus.json":
            resources = load_json(ROOT / "data" / "resources.json", [])
            graph = load_json(ROOT / "data" / "graph.json", {"nodes": []})
            progress = load_json(PROGRESS, {})
            return self._json(200, next_focus(graph, resources, progress))
        if path == "/data/catalog_meta.json":
            meta = load_json(ROOT / "data" / "catalog_meta.json", {})
            meta["git_sha"] = git_sha()
            return self._json(200, meta)
        return super().do_GET()

    def do_PUT(self):  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path not in PUT_PATHS:
            self.send_error(404)
            return
        host = self.client_address[0]
        if host not in LOOPBACK:
            self.send_error(403, "writes are localhost-only")
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode())
            if not isinstance(payload, dict):
                raise ValueError("object required")
        except (json.JSONDecodeError, ValueError):
            self.send_error(400, "invalid json")
            return
        if path == "/data/progress.json":
            resources = load_json(ROOT / "data" / "resources.json", [])
            graph = load_json(ROOT / "data" / "graph.json", {"nodes": []})
            progress = dict(payload)
            progress.setdefault("schema_version", 1)
            progress = rollup_all(progress, by_id(resources))
            PROGRESS.write_text(json.dumps(progress, indent=2) + "\n")
            return self._json(200, {"progress": progress, "focus": next_focus(graph, resources, progress)})
        if path == "/data/assignments.json":
            errs = validate_assignments(payload)
            if errs:
                self.send_error(400, errs[0])
                return
            if not SEED.exists():
                self.send_error(400, "graph.seed.json missing; compile the catalog first")
                return
            payload.setdefault("schema_version", 1)
            payload.setdefault("placements", {})
            ASSIGNMENTS.write_text(json.dumps(payload, indent=2) + "\n")
            resources = load_json(ROOT / "data" / "resources.json", [])
            known_ids = {r["id"] for r in resources if isinstance(r, dict) and r.get("id")}
            placements = filter_placements(payload["placements"], known_ids)
            seed = load_json(SEED, {"nodes": []})
            graph = load_json(ROOT / "data" / "graph.json", {"nodes": []})
            graph["nodes"] = apply_placements(seed.get("nodes") or [], placements)
            (ROOT / "data" / "graph.json").write_text(json.dumps(graph, indent=2) + "\n")
            return self._json(200, {"assignments": payload, "graph": graph})
        if path == "/data/roadmap_layout.json":
            checkpoints = payload.get("checkpoints", {})
            clusters = payload.get("clusters", {})
            if not isinstance(checkpoints, dict) or not isinstance(clusters, dict):
                self.send_error(400, "checkpoints and clusters must be objects")
                return
            payload.setdefault("schema_version", 1)
            payload["checkpoints"] = checkpoints
            payload["clusters"] = clusters
            LAYOUT.write_text(json.dumps(payload, indent=2) + "\n")
            return self._json(200, payload)
        self.send_error(404)

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main() -> None:
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    if not PROGRESS.exists():
        PROGRESS.write_text(json.dumps({"schema_version": 1}, indent=2) + "\n")
    try:
        httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as e:
        print(
            f"port {PORT} in use ({e}). Stop the other atlas: "
            f"launchctl unload ~/Library/LaunchAgents/com.sagar.ai-sme-map.plist "
            f"or change PORT in scripts/serve.py.",
            flush=True,
        )
        raise SystemExit(1)
    print(f"AI/ML SME Atlas  http://{HOST}:{PORT}", flush=True)
    print("Progress PUT is localhost-only. Do not bind 0.0.0.0.", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
