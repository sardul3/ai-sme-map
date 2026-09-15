import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestRoadmapView(unittest.TestCase):
    def test_given_roadmap_js_when_read_then_canvas_primitives(self):
        js = (ROOT / "web" / "roadmap.js").read_text()
        self.assertIn("renderRoadmap", js)
        self.assertIn("MUST", js)
        self.assertIn("ELECTIVE", js)
        self.assertIn("MAY", js)
        self.assertIn("Build", js)
        self.assertIn("viewBox", js)
        self.assertIn("unassigned", js.lower())
        self.assertTrue(
            "awesome-ml.md" in js or ("clusterKey" in js and 'endsWith(".md")' in js),
            "harvest cluster layout keys must be source filenames, not Harvest · labels",
        )

    def test_given_roadmap_page_when_read_then_board_and_scripts(self):
        html = (ROOT / "web" / "roadmap.html").read_text()
        self.assertIn('data-page="roadmap"', html)
        self.assertIn('id="board"', html)
        self.assertIn('src="roadmap.js"', html)

    def test_given_app_js_when_read_then_layout_atlas_and_roadmap_redraw(self):
        js = (ROOT / "web" / "app.js").read_text()
        self.assertIn("roadmap_layout.json", js)
        self.assertIn("globalThis.atlas", js)
        self.assertIn('PAGE === "roadmap"', js)
        self.assertIn("renderRoadmap", js)

    def test_given_styles_when_read_then_roadmap_board_canvas(self):
        css = (ROOT / "web" / "styles.css").read_text()
        self.assertIn(".roadmap-board svg", css)
        self.assertIn("calc(100vh - 12rem)", css)

    def test_given_roadmap_js_when_read_then_authoring_hooks(self):
        js = (ROOT / "web" / "roadmap.js").read_text()
        self.assertIn("isAuthor", js)
        self.assertIn("assignments.json", js)
        self.assertIn("localhost-only", js)
        self.assertIn("placements", js)
