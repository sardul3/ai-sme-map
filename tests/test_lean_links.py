"""Agent-facing lean catalog: unique title+url rows including lesson parts."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from compile_catalog import normalize  # noqa: E402
from export_static import export_static  # noqa: E402


def _course():
    parent = normalize("https://example.com/course")
    lecture = normalize("https://example.com/lecture-1")
    other = normalize("https://example.com/other")
    resources = [
        {
            "title": "Course",
            "url": parent,
            "audio_url": "https://cdn.example.com/episode.mp3",
            "parts": [
                {"title": "Lecture 1", "url": lecture},
                {"title": "Week slug", "url": None},
            ],
        },
        {"title": "Should not win", "url": lecture},
        {"title": "Other", "url": other},
    ]
    return parent, lecture, other, resources


class TestLeanLinks(unittest.TestCase):
    def test_given_parent_and_parts_when_flattened_then_unique_http_urls_only(self):
        from compile_catalog import lean_links

        parent, lecture, other, resources = _course()
        items = lean_links(resources)
        urls = [row["url"] for row in items]
        self.assertEqual(len(items), 3)
        self.assertEqual(set(urls), {parent, lecture, other})
        self.assertNotIn("https://cdn.example.com/episode.mp3", urls)
        lecture_row = next(row for row in items if row["url"] == lecture)
        self.assertEqual(lecture_row["title"], "Lecture 1")
        self.assertEqual([row["title"] for row in items], ["Course", "Lecture 1", "Other"])
        for row in items:
            self.assertEqual(set(row), {"title", "url"})

    def test_given_resources_when_document_built_then_v1_wrapper(self):
        from compile_catalog import links_document

        _, _, _, resources = _course()
        doc = links_document(resources, compiled_at="2026-09-20T00:00:00Z", git_sha="abc123")
        self.assertEqual(doc["schema"], "atlas.links.v1")
        self.assertEqual(doc["compiled_at"], "2026-09-20T00:00:00Z")
        self.assertEqual(doc["git_sha"], "abc123")
        self.assertEqual(doc["count"], len(doc["items"]))
        self.assertEqual(doc["count"], 3)

    def test_given_valid_doc_when_validated_then_no_errors(self):
        from compile_catalog import links_document
        from validate import validate_links

        _, _, _, resources = _course()
        doc = links_document(resources, compiled_at="t", git_sha="s")
        self.assertEqual(validate_links(resources, doc), [])

    def test_given_missing_schema_when_validated_then_error(self):
        from validate import validate_links

        _, _, _, resources = _course()
        errors = validate_links(resources, {"items": []})
        self.assertIn("links.json schema must be atlas.links.v1", errors)

    def test_given_count_mismatch_when_validated_then_error(self):
        from compile_catalog import links_document
        from validate import validate_links

        _, _, _, resources = _course()
        doc = links_document(resources, compiled_at="t", git_sha="s")
        doc["count"] = 0
        self.assertIn("links.json count mismatch", validate_links(resources, doc))

    def test_given_extra_item_key_when_validated_then_error(self):
        from compile_catalog import links_document
        from validate import validate_links

        _, _, _, resources = _course()
        doc = links_document(resources, compiled_at="t", git_sha="s")
        doc["items"][0]["id"] = "nope"
        errors = validate_links(resources, doc)
        self.assertTrue(any("exactly title and url" in err for err in errors))

    def test_given_url_not_in_flatten_when_validated_then_error(self):
        from compile_catalog import links_document
        from validate import validate_links

        _, _, _, resources = _course()
        doc = links_document(resources, compiled_at="t", git_sha="s")
        doc["items"].append({"title": "Ghost", "url": "https://example.com/ghost"})
        doc["count"] = len(doc["items"])
        self.assertIn("links.json URLs do not match catalog flatten", validate_links(resources, doc))


class TestLinksOnSite(unittest.TestCase):
    def test_given_index_html_when_read_then_agent_links_href(self):
        html = (ROOT / "web" / "index.html").read_text()
        self.assertIn('href="data/links.json"', html)

    def test_given_export_when_written_then_links_json_ships(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "dist"
            export_static(dest)
            path = dest / "data" / "links.json"
            self.assertTrue(path.is_file(), "links.json missing from Pages bundle")
            doc = json.loads(path.read_text())
            self.assertEqual(doc["schema"], "atlas.links.v1")
            self.assertEqual(doc["count"], len(doc["items"]))
