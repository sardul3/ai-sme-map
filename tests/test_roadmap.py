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

    def test_given_finish_chip_drag_when_read_then_save_before_state(self):
        js = (ROOT / "web" / "roadmap.js").read_text()
        start = js.index("async function finishChipDrag")
        end = js.index("async function finishGroupDrag")
        block = js[start:end]
        save_at = block.index("await atlas.saveAssignments")
        before_save = block[:save_at]
        self.assertNotIn("atlas.state.assignments =", before_save)

    def test_given_roadmap_js_when_library_drop_then_tombstone_without_seed(self):
        js = (ROOT / "web" / "roadmap.js").read_text()
        self.assertIn("!atlas.state.graphSeed", js)
        self.assertIn("placements[id] = null", js)

    def _fn_block(self, js, name):
        start = js.index(f"function {name}")
        nxt = js.find("\nfunction ", start + 1)
        return js[start:] if nxt < 0 else js[start:nxt]

    def test_given_default_checkpoint_when_shared_cell_then_fans_out(self):
        js = (ROOT / "web" / "roadmap.js").read_text()
        block = self._fn_block(js, "checkpointPos")
        self.assertNotIn(
            'const y = st.rail === "theory" ? 56 : 460;',
            block,
            "default y must not be the rail-only one-liner",
        )
        stacked = (
            "checkpointStack" in js
            or "checkpointHeight" in js
            or ("i *" in js and "24" in block)
        )
        self.assertTrue(
            stacked,
            "fan-out helper (checkpointStack / measured height / i *) must exist",
        )

    def test_given_default_cluster_when_missing_layout_then_uses_chip_height(self):
        js = (ROOT / "web" / "roadmap.js").read_text()
        block = self._fn_block(js, "clusterPos")
        self.assertNotIn("index * 240", block)
        uses_chips = "clusterHeight" in js or "nChips" in js or "CHIP_H" in block
        uses_prev = "previousCluster" in js or "prevCluster" in js or "prev." in block
        self.assertTrue(
            uses_chips or uses_prev,
            "cluster default y must use chip-count height or previousCluster, not only index * 240",
        )

    def test_given_successful_save_when_read_then_clears_roadmap_note(self):
        js = (ROOT / "web" / "roadmap.js").read_text()
        chip = js[js.index("async function finishChipDrag") : js.index("async function finishGroupDrag")]
        group = js[js.index("async function finishGroupDrag") : js.index("function bindPanZoom")]
        self.assertIn("setRoadmapNote", chip)
        self.assertIn('setRoadmapNote("")', chip)
        self.assertIn('setRoadmapNote("")', group)
        save_asg = chip.index("await atlas.saveAssignments")
        after_asg = chip[save_asg:]
        catch_asg = after_asg.index("catch")
        self.assertIn('setRoadmapNote("")', after_asg[:catch_asg])
        save_lay = group.index("await atlas.saveLayout")
        after_lay = group[save_lay:]
        catch_lay = after_lay.index("catch")
        self.assertIn('setRoadmapNote("")', after_lay[:catch_lay])
        snap = self._fn_block(js, "snapBack")
        self.assertIn("Assignments are localhost-only.", snap)

    def test_given_roadmap_js_when_read_then_listing_arrows(self):
        js = (ROOT / "web" / "roadmap.js").read_text()
        self.assertIn("roadmap-edge", js)
        self.assertIn("<line", js)
        self.assertIn("listingAnchors", js)
        self.assertIn("listingEdges", js)
        self.assertIn("marker-end", js)
        edges = self._fn_block(js, "listingEdges")
        self.assertIn("must", edges)
        self.assertIn("prereqs", edges)

    def test_given_roadmap_js_when_read_then_on_screen_zoom_controls(self):
        js = (ROOT / "web" / "roadmap.js").read_text()
        self.assertIn("roadmap-zoom-in", js)
        self.assertIn("roadmap-zoom-out", js)
        self.assertIn("roadmap-zoom-pct", js)
        self.assertTrue("SCALE_MAX" in js or "8" in js)
        self.assertIn("zoomBy", js)

    def test_given_chip_when_read_then_course_url_is_openable(self):
        js = (ROOT / "web" / "roadmap.js").read_text()
        chip = self._fn_block(js, "chipMarkup")
        self.assertIn("data-url", chip)
        self.assertIn("<a", chip)
        self.assertIn("href=", chip)
        self.assertIn("target=\"_blank\"", chip)
        finish = js[js.index("async function finishChipDrag") : js.index("async function finishGroupDrag")]
        self.assertIn("window.open", finish)
        self.assertIn("!drag.moved", finish)

    def test_given_layout_constants_when_read_then_columns_are_not_tight(self):
        js = (ROOT / "web" / "roadmap.js").read_text()
        self.assertIn("STAGE_GAP", js)
        self.assertIn("CHECKPOINT_W +", js)
        self.assertRegex(js, r"CHIP_W\s*=\s*(2[5-9]\d|[3-9]\d{2})")
        self.assertIn("laneX", js)
        self.assertIn("CLUSTER_COLS", js)

    def test_given_roadmap_js_when_read_then_viewbox_tracks_viewport(self):
        js = (ROOT / "web" / "roadmap.js").read_text()
        self.assertIn("syncViewBox", js)
        self.assertIn("getBoundingClientRect", js)
        self.assertNotIn("0 0 ${VIEW_W} ${VIEW_H}", js)
