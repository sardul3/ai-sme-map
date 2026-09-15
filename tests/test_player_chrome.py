import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestPlayerChrome(unittest.TestCase):
    def test_given_homepage_when_read_then_player_is_hidden(self):
        html = (ROOT / "web" / "index.html").read_text()
        self.assertIn('id="player"', html)
        self.assertIn('id="player" hidden', html)
        self.assertIn('id="player-dismiss"', html)
        self.assertIn('id="player-size"', html)

    def test_given_library_when_read_then_player_shell_exists_hidden(self):
        html = (ROOT / "web" / "library.html").read_text()
        self.assertIn('id="player" hidden', html)
        self.assertIn('id="player-audio"', html)

    def test_given_app_js_when_read_then_session_now_playing(self):
        js = (ROOT / "web" / "app.js").read_text()
        self.assertIn("atlas_now_playing", js)
        self.assertIn("atlas_player_size", js)
        self.assertIn("player-dismiss", js)
        self.assertIn("player-mini", js)
