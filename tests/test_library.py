import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from library import assigned_ids, category_of, grouped, unassigned  # noqa: E402
from weekly_onboard import (  # noqa: E402
    COMMUTE_FEEDS,
    HARVEST_REMOTES,
    commute_candidates,
    known_episode_keys,
    merge_inbox,
    write_harvest_file,
)


def _graph(*nodes):
    return {"nodes": list(nodes)}


class TestUnassignedSeam(unittest.TestCase):
    def test_given_station_and_commute_when_unassigned_then_only_library_rows(self):
        resources = [
            {"id": "r-do", "title": "Do", "url": "https://ex.com/do", "source": "curated"},
            {"id": "r-part", "title": "Part", "url": "https://ex.com/part", "kind": "lesson", "parent_id": "r-do"},
            {
                "id": "r-walk",
                "title": "Walk",
                "url": "https://ex.com/walk",
                "audio_url": "https://ex.com/w.mp3",
                "purpose": "learn",
                "source": "commute",
            },
            {
                "id": "r-harvest",
                "title": "Extra",
                "url": "https://ex.com/extra",
                "source": "awesome-ml.md",
                "kind": "repo",
                "branches": ["nlp"],
            },
            {
                "id": "r-curated",
                "title": "Orphan paper",
                "url": "https://arxiv.org/abs/1",
                "source": "curated",
                "kind": "paper",
                "featured": True,
                "branches": ["nlp"],
            },
        ]
        resources[0]["parts"] = [{"id": "r-part", "title": "Part"}]
        graph = _graph({"id": "s-a", "do": ["r-do"], "parallel": [], "skim": [], "project": []})
        rows = unassigned(resources, graph)
        ids = {r["id"] for r in rows}
        self.assertEqual(ids, {"r-harvest", "r-curated"})
        self.assertIn("r-do", assigned_ids(resources, graph))
        self.assertIn("r-part", assigned_ids(resources, graph))
        self.assertIn("r-walk", assigned_ids(resources, graph))

    def test_given_unassigned_when_grouped_then_ordered_by_category(self):
        rows = [
            {"id": "a", "title": "Zed", "source": "awesome-nlp.md", "kind": "repo"},
            {"id": "b", "title": "Alpha", "source": "awesome-nlp.md", "kind": "repo"},
            {"id": "c", "title": "Paper", "source": "curated", "kind": "paper", "featured": True},
        ]
        groups = grouped(rows)
        names = [g["category"] for g in groups]
        self.assertEqual(names[0], "Curated · featured")
        self.assertIn("Harvest · awesome-nlp", names)
        nlp = next(g for g in groups if g["category"].startswith("Harvest"))
        self.assertEqual([r["title"] for r in nlp["rows"]], ["Alpha", "Zed"])

    def test_given_harvest_row_when_categorized_then_harvest_label(self):
        self.assertEqual(category_of({"source": "books.md", "kind": "book"}), "Harvest · books")
        self.assertEqual(category_of({"source": "curated", "kind": "course", "featured": False}), "Curated · course")


class TestWeeklyOnboardSeam(unittest.TestCase):
    def test_given_known_episode_when_feed_repeats_then_not_a_candidate(self):
        episodes = [{"url": "https://ex.com/a", "audio_url": "https://ex.com/a.mp3", "title": "A"}]
        items = [
            {"title": "A", "url": "https://ex.com/a", "audio_url": "https://ex.com/a.mp3", "sitting_min": 20},
            {"title": "B", "url": "https://ex.com/b", "audio_url": "https://ex.com/b.mp3", "sitting_min": 22},
        ]
        new = commute_candidates(items, known_episode_keys(episodes))
        self.assertEqual([i["title"] for i in new], ["B"])

    def test_given_youtube_feed_item_when_filtered_then_dropped(self):
        items = [
            {
                "title": "Talk",
                "url": "https://www.youtube.com/watch?v=x",
                "audio_url": "https://www.youtube.com/watch?v=x",
                "sitting_min": 30,
            }
        ]
        self.assertEqual(commute_candidates(items, set()), [])

    def test_given_sitting_outside_window_when_filtered_then_dropped(self):
        items = [{"title": "Long", "url": "https://ex.com/l", "audio_url": "https://ex.com/l.mp3", "sitting_min": 90}]
        self.assertEqual(commute_candidates(items, set()), [])

    def test_given_harvest_body_when_written_then_file_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "awesome-ml.md"
            dest.write_text("old\n")
            write_harvest_file(dest, "# Awesome Machine Learning\nnew link\n")
            self.assertIn("new link", dest.read_text())

    def test_given_inbox_parts_when_merged_then_human_gate_note_present(self):
        blob = merge_inbox(
            harvested=["awesome-ml.md"],
            commute_new=[{"title": "B", "url": "https://ex.com/b", "audio_url": "https://ex.com/b.mp3"}],
            fetched_at="2026-09-13T12:00:00Z",
        )
        self.assertTrue(blob["human_gate"])
        self.assertIn("awesome-ml.md", blob["harvested"])
        self.assertEqual(blob["commute_candidates"][0]["title"], "B")

    def test_given_weekly_module_when_read_then_does_not_edit_ranked_tracks(self):
        text = (ROOT / "scripts" / "weekly_onboard.py").read_text()
        self.assertNotIn("graph_spec.py", text)
        self.assertNotIn("EPISODES.append", text)
        self.assertIn("HARVEST_REMOTES", text)
        self.assertGreaterEqual(len(HARVEST_REMOTES), 5)
        self.assertGreaterEqual(len(COMMUTE_FEEDS), 3)

    def test_given_workflow_when_read_then_weekly_pr_not_direct_main_rank(self):
        yml = (ROOT / ".github" / "workflows" / "weekly-onboard.yml").read_text()
        self.assertIn("cron:", yml)
        self.assertIn("weekly_onboard", yml)
        self.assertIn("compile_catalog", yml)
        self.assertIn("pull-requests: write", yml)
        self.assertIn("create-pull-request", yml)
        self.assertIn("human", yml.lower())


class TestLibraryUIContract(unittest.TestCase):
    def test_given_nav_when_read_then_three_tabs_on_each_page(self):
        for name in ("index.html", "commute.html", "library.html"):
            html = (ROOT / "web" / name).read_text()
            with self.subTest(name=name):
                self.assertIn('href="index.html"', html)
                self.assertIn('href="commute.html"', html)
                self.assertIn('href="library.html"', html)
                self.assertIn("Library · unassigned", html)

    def test_given_library_page_when_read_then_groups_and_search(self):
        html = (ROOT / "web" / "library.html").read_text()
        self.assertIn('data-page="library"', html)
        self.assertIn('id="library"', html)
        self.assertIn('id="q"', html)
        self.assertIn('id="hits"', html)

    def test_given_app_js_when_read_then_renders_unassigned_by_category(self):
        js = (ROOT / "web" / "app.js").read_text()
        self.assertIn("renderLibrary", js)
        self.assertIn("unassignedResources", js)
        self.assertIn("data-category", js)
        self.assertIn("library", js)

    def test_given_paths_when_library_then_data_dir_is_site_root(self):
        from atlas_paths import atlas_root
        from serve import resolve_public_path

        self.assertEqual(atlas_root("/library.html"), "/")
        self.assertEqual(atlas_root("/ai-sme-map/library.html"), "/ai-sme-map/")
        self.assertEqual(resolve_public_path("/library"), "/web/library.html")
        self.assertEqual(resolve_public_path("/library.html"), "/web/library.html")


if __name__ == "__main__":
    unittest.main()
