"""Contracts for GitHub Pages: relative assets, empty public progress, commute export."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from atlas_paths import atlas_root  # noqa: E402
from export_static import export_static  # noqa: E402
from serve import resolve_public_path  # noqa: E402


class TestAtlasRoot(unittest.TestCase):
    def test_given_request_paths_when_atlas_root_then_data_dir_is_site_root(self):
        cases = {
            "/": "/",
            "/index.html": "/",
            "/commute": "/",
            "/commute.html": "/",
            "/web/index.html": "/",
            "/ai-sme-map": "/ai-sme-map/",
            "/ai-sme-map/": "/ai-sme-map/",
            "/ai-sme-map/commute": "/ai-sme-map/",
            "/ai-sme-map/commute.html": "/ai-sme-map/",
            "/ai-sme-map/web/index.html": "/ai-sme-map/",
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual(atlas_root(path), expected)


class TestServePublicPaths(unittest.TestCase):
    def test_given_pretty_urls_when_resolved_then_web_files(self):
        self.assertEqual(resolve_public_path("/"), "/web/index.html")
        self.assertEqual(resolve_public_path("/index.html"), "/web/index.html")
        self.assertEqual(resolve_public_path("/commute"), "/web/commute.html")
        self.assertEqual(resolve_public_path("/commute.html"), "/web/commute.html")
        self.assertEqual(resolve_public_path("/styles.css"), "/web/styles.css")
        self.assertEqual(resolve_public_path("/app.js"), "/web/app.js")
        self.assertEqual(resolve_public_path("/data/graph.json"), "/data/graph.json")


class TestRelativeAssets(unittest.TestCase):
    def test_given_html_when_read_then_assets_are_relative(self):
        for name in ("index.html", "commute.html"):
            html = (ROOT / "web" / name).read_text()
            with self.subTest(name=name):
                self.assertIn('href="styles.css"', html)
                self.assertIn('src="app.js"', html)
                self.assertNotIn("/web/styles.css", html)
                self.assertNotIn("/web/app.js", html)

    def test_given_app_js_when_read_then_fetches_use_data_href(self):
        js = (ROOT / "web" / "app.js").read_text()
        self.assertIn("function dataHref", js)
        self.assertIn("function atlasRoot", js)
        self.assertNotIn('fetch("/data/graph.json")', js)
        self.assertNotIn('fetch("/data/progress.json"', js)


class TestExportStatic(unittest.TestCase):
    def test_given_export_when_written_then_pages_bundle_is_flat_and_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "dist"
            export_static(dest)
            self.assertTrue((dest / "index.html").is_file())
            self.assertTrue((dest / "commute.html").is_file())
            self.assertTrue((dest / "app.js").is_file())
            self.assertTrue((dest / "styles.css").is_file())
            self.assertTrue((dest / "data" / "graph.json").is_file())
            self.assertTrue((dest / "data" / "resources.json").is_file())
            self.assertTrue((dest / ".nojekyll").is_file())
            progress = json.loads((dest / "data" / "progress.json").read_text())
            self.assertEqual(set(progress), {"schema_version"})
            self.assertEqual(progress["schema_version"], 1)
            html = (dest / "index.html").read_text()
            self.assertIn('href="commute.html"', html)
            self.assertIn('href="styles.css"', html)


class TestPagesWorkflow(unittest.TestCase):
    def test_given_pages_workflow_when_read_then_exports_and_deploys(self):
        text = (ROOT / ".github" / "workflows" / "pages.yml").read_text()
        self.assertIn("export_static", text)
        self.assertIn("deploy-pages", text)
        self.assertIn("pages: write", text)
        self.assertIn("id-token: write", text)


if __name__ == "__main__":
    unittest.main()
