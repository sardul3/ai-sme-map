import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from compile_catalog import normalize
from outlines import OUTLINES


class TestMoreOutlines(unittest.TestCase):
    def test_zero_to_hero_has_lesson_parts(self):
        key = normalize("https://karpathy.ai/zero-to-hero.html")
        self.assertIn(key, OUTLINES)
        self.assertGreaterEqual(len(OUTLINES[key]), 7)

    def test_hf_nlp_course_has_chapter_parts(self):
        key = normalize("https://huggingface.co/learn/nlp-course")
        self.assertIn(key, OUTLINES)
        self.assertGreaterEqual(len(OUTLINES[key]), 7)

    def test_sktime_docs_keep_www(self):
        self.assertEqual(
            normalize("https://www.sktime.net/en/stable/"),
            "https://www.sktime.net/en/stable",
        )

    def test_strang_18_06_has_lecture_parts(self):
        key = normalize("https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/")
        self.assertIn(key, OUTLINES)
        self.assertGreaterEqual(len(OUTLINES[key]), 20)

    def test_hf_diffusion_has_units(self):
        key = normalize("https://huggingface.co/learn/diffusion-course")
        self.assertIn(key, OUTLINES)
        self.assertGreaterEqual(len(OUTLINES[key]), 5)

    def test_cs188_has_slug_projects(self):
        key = normalize("https://inst.eecs.berkeley.edu/~cs188/")
        self.assertIn(key, OUTLINES)
        self.assertGreaterEqual(len(OUTLINES[key]), 5)

    def test_statquest_has_slug_sittings(self):
        key = normalize("https://www.youtube.com/@statquest")
        self.assertIn(key, OUTLINES)
        self.assertGreaterEqual(len(OUTLINES[key]), 5)
