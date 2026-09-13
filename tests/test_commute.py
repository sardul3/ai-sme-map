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
        "purpose": "learn",
        "rank": 0,
        "sitting_min": 29,
    }
    row.update(overrides)
    return row


class TestCommutePlaylist(unittest.TestCase):
    def test_given_episodes_when_playlist_then_sorted_by_purpose_then_rank(self):
        episodes = [
            {"title": "Zebra lesson", "purpose": "learn", "rank": 1},
            {"title": "Alpha lesson", "purpose": "learn", "rank": 0},
            {"title": "Chat", "purpose": "interview", "rank": 0},
            {"title": "News", "purpose": "pulse", "rank": 0},
            {"title": "Orphan", "purpose": "other", "rank": 0},
        ]
        rows = playlist(episodes)
        self.assertEqual([r["title"] for r in rows], ["Alpha lesson", "Zebra lesson", "Chat", "News"])


class TestCommuteEpisodeRules(unittest.TestCase):
    def test_given_valid_enclosure_when_checked_then_no_errors(self):
        self.assertEqual(episode_errors(_ep()), [])

    def test_given_sitting_outside_12_75_when_checked_then_error(self):
        errs = episode_errors(_ep(sitting_min=90), {})
        self.assertTrue(any("sitting" in e for e in errs))

    def test_given_sitting_50_when_checked_then_ok_for_long_lesson(self):
        self.assertEqual(episode_errors(_ep(sitting_min=50)), [])

    def test_given_youtube_only_when_checked_then_error(self):
        errs = episode_errors(
            _ep(audio_url="https://www.youtube.com/watch?v=abc", url="https://www.youtube.com/watch?v=abc"),
        )
        self.assertTrue(any("enclosure" in e or "youtube" in e for e in errs))

    def test_given_missing_audio_url_when_checked_then_error(self):
        errs = episode_errors(_ep(audio_url=""))
        self.assertTrue(any("enclosure" in e or "audio_url" in e for e in errs))

    def test_given_unknown_purpose_when_checked_then_error(self):
        errs = episode_errors(_ep(purpose="homework"))
        self.assertTrue(any("purpose" in e for e in errs))

    def test_given_interview_purpose_when_checked_then_ok(self):
        self.assertEqual(episode_errors(_ep(purpose="interview", rank=1)), [])


class TestCommuteResource(unittest.TestCase):
    def test_given_episode_when_to_resource_then_podcast_fields_set(self):
        rec = to_resource(_ep())
        self.assertEqual(rec["kind"], "podcast")
        self.assertEqual(rec["audio_url"], _ep()["audio_url"])
        self.assertEqual(rec["purpose"], "learn")
        self.assertEqual(rec["rank"], 0)
        self.assertIn("29", rec["sitting"])
        self.assertFalse(rec.get("featured"))
        self.assertNotIn("station_id", rec)


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
                "purpose": "learn",
                "rank": 0,
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
                "purpose": "learn",
                "rank": 0,
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
            self.assertEqual(episode_errors(ep), [])
        purposes = {ep.get("purpose") for ep in EPISODES}
        self.assertTrue({"learn", "interview", "apply", "pulse"} <= purposes)


class TestCompiledCommute(unittest.TestCase):
    def test_given_compiled_catalog_when_read_then_seeded_playlist_and_feed_exist(self):
        root = Path(__file__).resolve().parents[1]
        resources = __import__("json").loads((root / "data" / "resources.json").read_text())
        graph = __import__("json").loads((root / "data" / "graph.json").read_text())
        feed = root / "data" / "feed.xml"
        commute = [r for r in resources if r.get("kind") == "podcast" and r.get("audio_url")]
        self.assertGreaterEqual(len(commute), 40)
        providers = {r.get("provider") for r in commute}
        self.assertGreaterEqual(len(providers), 5)
        purposes = {r.get("purpose") for r in commute}
        self.assertTrue({"learn", "interview", "apply", "pulse"} <= purposes)
        blob = " ".join(f'{r.get("provider","")} {r.get("url","")}' for r in commute).lower()
        self.assertTrue("ocdevel" in blob or "machinelearningguide" in blob)
        self.assertTrue("linear-digressions" in blob or "lineardigressions" in blob)
        self.assertTrue("talking-machines" in blob or "talkingmachines" in blob)
        self.assertTrue("dataskeptic" in blob)
        self.assertTrue("practical-ai" in blob or "practicalai" in blob or "changelog" in blob)
        self.assertTrue("twiml" in blob)
        self.assertTrue("latent" in blob)
        for rec in commute:
            self.assertIn(rec.get("purpose"), {"learn", "interview", "apply", "pulse"})
            self.assertIsInstance(rec.get("rank"), int)
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

    def test_given_commute_page_when_read_then_map_drawer_player_deck(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "web" / "commute.html").read_text()
        self.assertIn('id="map"', html)
        self.assertIn('id="drawer"', html)
        self.assertNotIn("Same dual rail as Tonight", html)
        self.assertIn('id="player"', html)
        self.assertIn('id="player-next"', html)
        self.assertIn('id="player-elapsed"', html)
        self.assertIn("data-skip", html)
        self.assertIn('id="harvest"', html)
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
        self.assertIn("playCommuteRelative", js)
        self.assertIn("formatClock", js)
        self.assertIn("renderPurposeMap", js)
        self.assertIn("data-purpose", js)


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
