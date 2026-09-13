import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


class TestAttachOutlines(unittest.TestCase):
    def test_slug_only_part_is_not_a_catalog_url(self):
        from compile_catalog import attach_outlines, make_id, normalize

        parent_url = normalize("https://coursera.org/specializations/machine-learning-introduction")
        parent = {
            "id": make_id(parent_url),
            "title": "Ng spec",
            "url": parent_url,
            "kind": "course",
            "featured": True,
            "source": "curated",
        }
        outlines = {parent_url: [{"slug": "week-1", "title": "Week 1", "url": None}]}
        resources = attach_outlines([parent], outlines)
        self.assertEqual(len(resources), 1)
        self.assertEqual(resources[0]["parts"][0]["id"], f"{parent['id']}:week-1")
        self.assertIsNone(resources[0]["parts"][0]["url"])

    def test_url_part_upserts_lesson_row(self):
        from compile_catalog import attach_outlines, make_id, normalize

        parent_url = normalize("https://course.fast.ai")
        lesson_url = normalize("https://course.fast.ai/Lessons/lesson1.html")
        parent = {
            "id": make_id(parent_url),
            "title": "fast.ai",
            "url": parent_url,
            "kind": "course",
            "featured": True,
            "source": "curated",
        }
        outlines = {parent_url: [{"slug": "lesson1", "title": "Lesson 1", "url": lesson_url}]}
        resources = attach_outlines([parent], outlines)
        self.assertEqual(len(resources), 2)
        child = next(r for r in resources if r["url"] == lesson_url)
        self.assertEqual(child["kind"], "lesson")
        self.assertEqual(child["parent_id"], parent["id"])
