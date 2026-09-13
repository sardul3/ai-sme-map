import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_links import classify, is_stale


class TestLinkClassify(unittest.TestCase):
    def test_404_and_410_fail_ci(self):
        self.assertEqual(classify("404"), "fail")
        self.assertEqual(classify("410"), "fail")

    def test_flaky_network_is_warn_not_fail(self):
        self.assertEqual(classify("HTTP 429"), "warn")
        self.assertEqual(classify("HTTP 500"), "warn")
        self.assertEqual(classify("URLError"), "warn")
        self.assertEqual(classify("TimeoutError"), "warn")

    def test_ok(self):
        self.assertEqual(classify(None), "ok")


class TestStale(unittest.TestCase):
    def test_older_than_90_days_is_stale(self):
        old = (datetime.now(timezone.utc) - timedelta(days=91)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.assertTrue(is_stale(old, days=90))

    def test_recent_last_ok_is_not_stale(self):
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.assertFalse(is_stale(now, days=90))

    def test_missing_last_ok_is_not_stale(self):
        self.assertFalse(is_stale(None, days=90))
