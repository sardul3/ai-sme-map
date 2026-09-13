import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from commute import EPISODES, episode_errors, playlist, to_resource, validate_commute, write_feed
from focus import next_focus


def _ep(**overrides):
    row = {
        "title": "Linear machines",
        "url": "https://www.learningmachines101.com/linear/",
        "audio_url": "https://traffic.libsyn.com/learningmachines101/LM101-082.mp3",
        "station_id": "s-la-work",
        "sitting_min": 29,
    }
    row.update(overrides)
    return row


class TestCommutePlaylist(unittest.TestCase):
    def test_given_episodes_when_playlist_then_sorted_by_station_order_then_title(self):
        stations = [
            {"id": "s-la-see", "stage": 0, "title": "See matrices"},
            {"id": "s-ml-intuit", "stage": 1, "title": "Algorithms"},
            {"id": "s-theory", "stage": 6, "title": "Later"},
        ]
        episodes = [
            {"title": "Zebra talk", "station_id": "s-la-see"},
            {"title": "Alpha talk", "station_id": "s-la-see"},
            {"title": "ML talk", "station_id": "s-ml-intuit"},
            {"title": "Too late", "station_id": "s-theory"},
            {"title": "Orphan", "station_id": "s-missing"},
        ]
        rows = playlist(episodes, stations)
        self.assertEqual([r["title"] for r in rows], ["Alpha talk", "Zebra talk", "ML talk"])


class TestCommuteEpisodeRules(unittest.TestCase):
    def test_given_valid_enclosure_when_checked_then_no_errors(self):
        self.assertEqual(episode_errors(_ep(), {"s-la-work"}), [])

    def test_given_sitting_outside_15_45_when_checked_then_error(self):
        errs = episode_errors(_ep(sitting_min=50), {"s-la-work"})
        self.assertTrue(any("sitting" in e for e in errs))

    def test_given_youtube_only_when_checked_then_error(self):
        errs = episode_errors(
            _ep(audio_url="https://www.youtube.com/watch?v=abc", url="https://www.youtube.com/watch?v=abc"),
            {"s-la-work"},
        )
        self.assertTrue(any("enclosure" in e or "youtube" in e for e in errs))

    def test_given_missing_audio_url_when_checked_then_error(self):
        errs = episode_errors(_ep(audio_url=""), {"s-la-work"})
        self.assertTrue(any("enclosure" in e or "audio_url" in e for e in errs))

    def test_given_station_not_t0_t5_when_checked_then_error(self):
        errs = episode_errors(_ep(station_id="s-theory"), {"s-la-work"})
        self.assertTrue(any("station" in e for e in errs))


class TestCommuteResource(unittest.TestCase):
    def test_given_episode_when_to_resource_then_podcast_fields_set(self):
        rec = to_resource(_ep())
        self.assertEqual(rec["kind"], "podcast")
        self.assertEqual(rec["audio_url"], _ep()["audio_url"])
        self.assertEqual(rec["station_id"], "s-la-work")
        self.assertIn("29", rec["sitting"])
        self.assertFalse(rec.get("featured"))


class TestCommuteCatalogValidate(unittest.TestCase):
    def test_given_no_commute_rows_when_validated_then_ok(self):
        nodes = [{"id": "s-la-see", "stage": 0, "do": ["r-x"]}]
        self.assertEqual(validate_commute([], nodes), [])

    def test_given_bad_catalog_row_when_validated_then_error(self):
        nodes = [{"id": "s-la-see", "stage": 0}]
        resources = [
            {
                "title": "Bad",
                "url": "https://example.com/bad",
                "kind": "podcast",
                "audio_url": "",
                "station_id": "s-la-see",
                "sitting_min": 20,
            }
        ]
        errs = validate_commute(resources, nodes)
        self.assertTrue(errs)


class TestCommuteFocusIsolation(unittest.TestCase):
    def test_given_commute_marked_done_when_focus_then_do_rail_unchanged(self):
        graph = {"nodes": [{"id": "s-la-see", "title": "See", "stage": 0, "do": ["r-do"]}]}
        resources = [
            {"id": "r-do", "title": "Do item", "url": "https://example.com/do"},
            {
                "id": "r-commute",
                "title": "Commute item",
                "url": "https://example.com/audio-page",
                "kind": "podcast",
                "audio_url": "https://example.com/a.mp3",
                "station_id": "s-la-see",
            },
        ]
        empty = next_focus(graph, resources, {})
        ticked = next_focus(graph, resources, {"r-commute": "done"})
        self.assertEqual(empty["resource_id"], "r-do")
        self.assertEqual(ticked["resource_id"], "r-do")


class TestCommuteLinks(unittest.TestCase):
    def test_given_commute_resource_when_collect_urls_then_includes_page_and_enclosure(self):
        # collect_urls reads data/; this asserts the helper used by check_links
        from check_links import commute_urls

        resources = [
            {
                "url": "https://example.com/notes",
                "audio_url": "https://example.com/ep.mp3",
                "featured": False,
            }
        ]
        urls = commute_urls(resources)
        self.assertIn("https://example.com/notes", urls)
        self.assertIn("https://example.com/ep.mp3", urls)


class TestCommuteSeed(unittest.TestCase):
    def test_given_curated_seed_when_checked_then_at_least_one_valid_enclosure(self):
        t0_t5 = {
            "s-la-see",
            "s-la-work",
            "s-calc",
            "s-prob",
            "s-proofs",
            "s-numerical",
            "s-ml-intuit",
            "s-ml-do",
            "s-unsupervised",
            "s-trees",
            "s-eval",
            "s-search",
            "s-logic",
            "s-games",
            "s-kg",
            "s-backprop",
            "s-ship-net",
            "s-cv",
            "s-seq",
            "s-ssl",
            "s-diffusion",
            "s-gnn",
            "s-attn",
            "s-ir",
            "s-llm-tools",
            "s-llm-from-scratch",
            "s-speech",
            "s-llm-eval",
            "s-agents",
            "s-agent-eval",
            "s-multimodal",
            "s-code-llm",
            "s-ssm",
            "s-rl",
            "s-drl",
            "s-bandits",
            "s-imitation",
            "s-marl",
            "s-world-models",
            "s-data-ml",
            "s-sys",
            "s-eval-prod",
            "s-compilers",
            "s-privacy",
        }
        self.assertGreaterEqual(len(EPISODES), 1)
        for ep in EPISODES:
            self.assertEqual(episode_errors(ep, t0_t5), [])


class TestCompiledCommute(unittest.TestCase):
    def test_given_compiled_catalog_when_read_then_seeded_playlist_and_feed_exist(self):
        root = Path(__file__).resolve().parents[1]
        resources = __import__("json").loads((root / "data" / "resources.json").read_text())
        graph = __import__("json").loads((root / "data" / "graph.json").read_text())
        feed = root / "data" / "feed.xml"
        commute = [r for r in resources if r.get("kind") == "podcast" and r.get("audio_url")]
        self.assertGreaterEqual(len(commute), 1)
        for rec in commute:
            self.assertIn(rec.get("station_id"), {n["id"] for n in graph["nodes"] if n["stage"] <= 5})
            self.assertTrue(rec["audio_url"].lower().endswith((".mp3", ".m4a")))
        self.assertTrue(feed.exists())
        text = feed.read_text().lower()
        self.assertIn("unpublished", text)
        self.assertIn(commute[0]["audio_url"].lower(), text)


class TestCommuteUIContract(unittest.TestCase):
    def test_given_index_when_read_then_commute_is_a_link_not_a_playlist(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "web" / "index.html").read_text()
        self.assertIn('href="commute.html"', html)
        self.assertIn("Commute · eyes-off", html)
        self.assertNotIn('id="commute"', html)
        self.assertIn('id="player"', html)

    def test_given_commute_page_when_read_then_playlist_player_and_harvest_exist(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "web" / "commute.html").read_text()
        self.assertIn('id="commute"', html)
        self.assertIn('id="player"', html)
        self.assertIn('id="harvest"', html)
        self.assertIn('id="q"', html)
        self.assertIn('href="index.html"', html)

    def test_given_app_js_when_read_then_in_atlas_play_and_media_session(self):
        js = (Path(__file__).resolve().parents[1] / "web" / "app.js").read_text()
        self.assertIn("mediaSession", js)
        self.assertIn("atlas_commute_pos", js)
        self.assertIn('data-commute-play', js)
        self.assertIn("playbackRate", js)
        self.assertRegex(js, r'key === ["\'] ["\']|key === ["\']Space["\']|ev.code === ["\']Space["\']')
        self.assertIn("keyboard_done", js)
        self.assertIn("renderHarvest", js)


class TestCommuteFeed(unittest.TestCase):
    def test_given_playlist_when_feed_written_then_enclosures_match_and_unpublished(self):
        rows = [
            _ep(title="Alpha", audio_url="https://example.com/a.mp3", url="https://example.com/a"),
            _ep(title="Beta", audio_url="https://example.com/b.m4a", url="https://example.com/b"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "feed.xml"
            write_feed(rows, path)
            text = path.read_text()
            self.assertIn("unpublished", text.lower())
            self.assertIn("not for public", text.lower())
            root = ET.fromstring(text)
            encs = [n.get("url") for n in root.findall(".//enclosure")]
            self.assertEqual(encs, ["https://example.com/a.mp3", "https://example.com/b.m4a"])


if __name__ == "__main__":
    unittest.main()
