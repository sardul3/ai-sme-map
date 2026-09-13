import unittest

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


class TestServeBind(unittest.TestCase):
    def test_loopback_hosts_include_ipv4_and_ipv6(self):
        import serve

        self.assertIn("127.0.0.1", serve.LOOPBACK)
        self.assertIn("::1", serve.LOOPBACK)
        self.assertEqual(serve.HOST, "127.0.0.1")

    def test_git_sha_is_never_blank(self):
        import serve

        self.assertTrue(serve.git_sha())
