import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from eval_slo import do_rail_slo_ok, time_to_first_done_ms


class TestEvalSlo(unittest.TestCase):
    def test_time_to_first_done(self):
        events = [
            {"t": 1000, "event": "load"},
            {"t": 1500, "event": "focus_status", "st": "doing"},
            {"t": 4000, "event": "focus_status", "st": "done"},
        ]
        self.assertEqual(time_to_first_done_ms(events), 3000)

    def test_keyboard_done_counts(self):
        events = [{"t": 10, "event": "load"}, {"t": 110, "event": "keyboard_done"}]
        self.assertEqual(time_to_first_done_ms(events), 100)

    def test_incomplete_log_is_none(self):
        self.assertIsNone(time_to_first_done_ms([{"t": 1, "event": "load"}]))

    def test_slo_fails_on_do_404(self):
        status = {"urls": {"https://example.com/gone": {"ok": False, "error": "404"}}}
        self.assertFalse(do_rail_slo_ok(status))

    def test_slo_ok_when_only_warns(self):
        status = {"urls": {"https://example.com/slow": {"ok": False, "error": "HTTP 429"}}}
        self.assertTrue(do_rail_slo_ok(status))
