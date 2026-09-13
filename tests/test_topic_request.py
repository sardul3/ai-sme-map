import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from topic_request import (  # noqa: E402
    github_awesome_query,
    harvest_filename,
    is_allowed_harvest_url,
    issue_comment_body,
    load_sources_table,
    match_shelf,
    normalize_topic,
    parse_topic,
    pick_awesome_repo,
    shelf_has_hits,
    write_topic_harvest,
)

HARVEST = [
    {"name": "awesome-nlp.md", "role": "NLP list"},
    {"name": "awesome-rl.md", "role": "RL list"},
    {"name": "awesome-ml.md", "role": "ML libraries and software list"},
]

STATIONS = [
    {
        "id": "s-agent-graphs",
        "title": "Loops, tools, other agents",
        "branch": "agents",
        "why": "LangGraph, MCP, multi-agent. Still no backprop required.",
    },
    {
        "id": "s-attn",
        "title": "Attention is the API",
        "branch": "nlp",
        "why": "Transformers after you can train a net.",
    },
]

RESOURCES = [
    {
        "id": "r-lg",
        "title": "LangGraph overview",
        "featured": True,
        "source": "curated",
        "branches": ["agents"],
        "url": "https://docs.langchain.com/oss/python/langgraph/overview",
    },
    {
        "id": "r-harvest-nlp",
        "title": "Some NLP repo",
        "featured": False,
        "source": "awesome-nlp.md",
        "branches": ["nlp"],
        "url": "https://github.com/ex/nlp",
    },
]


class TestNormalizeAndParse(unittest.TestCase):
    def test_given_messy_title_when_normalized_then_slug_tokens(self):
        self.assertEqual(normalize_topic("  LangGraph,  "), "langgraph")
        self.assertEqual(parse_topic("topic: NLP"), "nlp")
        self.assertEqual(parse_topic("topic: claude code"), "claude code")

    def test_given_topic_when_named_then_harvest_file_and_github_query(self):
        self.assertEqual(harvest_filename("LangGraph"), "topic-langgraph.md")
        self.assertEqual(harvest_filename("claude code"), "topic-claude-code.md")
        q = github_awesome_query("nlp")
        self.assertIn("awesome", q.lower())
        self.assertIn("nlp", q.lower())


class TestMatchShelf(unittest.TestCase):
    def test_given_nlp_when_matched_then_harvest_list_not_papers(self):
        hits = match_shelf("nlp", HARVEST, STATIONS, RESOURCES)
        names = [h["name"] for h in hits["harvest"]]
        self.assertIn("awesome-nlp.md", names)
        self.assertNotIn("awesome-rl.md", names)
        self.assertTrue(any(s["id"] == "s-attn" for s in hits["stations"]))
        leftovers = [r["id"] for r in hits["resources"]]
        self.assertNotIn("r-harvest-nlp", leftovers)

    def test_given_awesome_nlp_when_matched_then_same_list(self):
        hits = match_shelf("awesome-nlp", HARVEST, STATIONS, RESOURCES)
        self.assertEqual([h["name"] for h in hits["harvest"]], ["awesome-nlp.md"])

    def test_given_langgraph_when_matched_then_station_and_featured(self):
        hits = match_shelf("langgraph", HARVEST, STATIONS, RESOURCES)
        self.assertEqual(hits["harvest"], [])
        self.assertTrue(any(s["id"] == "s-agent-graphs" for s in hits["stations"]))
        self.assertTrue(any(r["id"] == "r-lg" for r in hits["featured"]))
        self.assertTrue(shelf_has_hits(hits))

    def test_given_unknown_topic_when_matched_then_empty(self):
        hits = match_shelf("neuro-symbolic-foo", HARVEST, STATIONS, RESOURCES)
        self.assertFalse(shelf_has_hits(hits))
        self.assertEqual(hits["harvest"], [])
        self.assertEqual(hits["stations"], [])
        self.assertEqual(hits["featured"], [])
        self.assertEqual(hits["resources"], [])


class TestScrapeGuard(unittest.TestCase):
    def test_given_youtube_or_coursera_when_checked_then_refused(self):
        self.assertFalse(is_allowed_harvest_url("https://www.youtube.com/watch?v=dQw4w9wg"))
        self.assertFalse(is_allowed_harvest_url("https://www.coursera.org/learn/nlp"))
        self.assertFalse(is_allowed_harvest_url("https://example.com/awesome-nlp"))

    def test_given_github_awesome_readme_when_checked_then_allowed(self):
        self.assertTrue(
            is_allowed_harvest_url(
                "https://raw.githubusercontent.com/keon/awesome-nlp/master/README.md"
            )
        )
        self.assertTrue(is_allowed_harvest_url("https://github.com/keon/awesome-nlp"))


class TestIssueComment(unittest.TestCase):
    def test_given_hits_when_commented_then_lists_shelf(self):
        hits = match_shelf("nlp", HARVEST, STATIONS, RESOURCES)
        body = issue_comment_body(hits=hits)
        self.assertIn("awesome-nlp.md", body)
        self.assertIn("Already on the shelf", body)
        self.assertNotIn("opened a harvest PR", body)

    def test_given_scrape_pr_when_commented_then_human_gate(self):
        body = issue_comment_body(scrape_pr="https://github.com/sardul3/ai-sme-map/pull/9")
        self.assertIn("pull/9", body)
        self.assertIn("Library", body)
        self.assertIn("do rail", body.lower().replace("-", " "))

    def test_given_nothing_when_commented_then_stop(self):
        body = issue_comment_body(none=True)
        self.assertIn("no awesome", body.lower())
        self.assertIn("stop", body.lower())


class TestPickAndWrite(unittest.TestCase):
    def test_given_search_items_when_picked_then_awesome_repo_for_topic(self):
        items = [
            {"name": "notes", "html_url": "https://github.com/a/notes"},
            {
                "name": "awesome-nlp",
                "html_url": "https://github.com/keon/awesome-nlp",
                "full_name": "keon/awesome-nlp",
            },
        ]
        picked = pick_awesome_repo(items, "nlp")
        self.assertEqual(picked["name"], "awesome-nlp")

    def test_given_coursera_url_when_picked_then_none(self):
        items = [{"name": "awesome-nlp", "html_url": "https://www.coursera.org/learn/nlp"}]
        self.assertIsNone(pick_awesome_repo(items, "nlp"))

    def test_given_topic_when_written_then_topic_slug_file(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = write_topic_harvest("Claude Code", "# awesome\n" + "x" * 200, Path(tmp))
            self.assertEqual(path.name, "topic-claude-code.md")
            self.assertTrue(path.read_text().startswith("# awesome"))

    def test_given_sources_table_when_parsed_then_roles(self):
        rows = load_sources_table((ROOT / "harvest" / "SOURCES.md").read_text())
        names = {r["name"] for r in rows}
        self.assertIn("awesome-nlp.md", names)
        nlp = next(r for r in rows if r["name"] == "awesome-nlp.md")
        self.assertIn("NLP", nlp["role"])


class TestTopicRequestUIContract(unittest.TestCase):
    def test_given_pages_when_read_then_topic_box_not_live_search(self):
        for name in ("index.html", "commute.html", "library.html"):
            html = (ROOT / "web" / name).read_text()
            with self.subTest(name=name):
                self.assertIn("What are you trying to learn?", html)
                self.assertNotIn("Search the catalog", html)
                self.assertIn("langgraph", html.lower())
                self.assertIn('id="find"', html)
                self.assertIn('id="q"', html)
                self.assertIn('id="hits"', html)

    def test_given_app_js_when_read_then_submit_matches_shelf(self):
        js = (ROOT / "web" / "app.js").read_text()
        self.assertIn("matchShelf", js)
        self.assertIn("renderTopicHits", js)
        self.assertIn("topicIssueHref", js)
        self.assertIn("File a topic request", js)
        self.assertNotIn('$("q")?.addEventListener("input"', js)
        self.assertNotIn("renderHits(", js)
        self.assertIn('addEventListener("submit"', js)
        self.assertIn("github_repo", js)

    def test_given_compiled_meta_when_read_then_github_repo_and_harvest_lists(self):
        meta = __import__("json").loads((ROOT / "data" / "catalog_meta.json").read_text())
        self.assertEqual(meta.get("github_repo"), "sardul3/ai-sme-map")
        names = [r["name"] for r in meta.get("harvest_lists") or []]
        self.assertIn("awesome-nlp.md", names)


class TestTopicRequestWorkflow(unittest.TestCase):
    def test_given_workflow_when_read_then_issue_label_and_human_gate(self):
        yml = (ROOT / ".github" / "workflows" / "topic-request.yml").read_text()
        self.assertIn("issues:", yml)
        self.assertIn("topic-request", yml)
        self.assertIn("topic_request.py", yml)
        self.assertIn("create-pull-request", yml)
        self.assertIn("human", yml.lower())
        self.assertIn("Do rail", yml.replace("-", " ") + yml)
        self.assertNotIn("graph_spec", yml)
        self.assertNotIn("commute.py", yml)

    def test_given_issue_template_when_read_then_labeled_topic_request(self):
        path = ROOT / ".github" / "ISSUE_TEMPLATE" / "topic_request.yml"
        text = path.read_text()
        self.assertIn("topic-request", text)
        self.assertIn("topic:", text.lower())

    def test_given_script_when_read_then_does_not_edit_ranked_tracks(self):
        text = (ROOT / "scripts" / "topic_request.py").read_text()
        self.assertNotIn("graph_spec.py", text)
        self.assertNotIn("EPISODES.append", text)
        self.assertNotIn("HARVEST_REMOTES[", text)
