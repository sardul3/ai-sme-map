import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestBuilderPath(unittest.TestCase):
    def test_given_compiled_graph_when_read_then_builder_stations_follow_core_ml(self):
        graph = json.loads((ROOT / "data" / "graph.json").read_text())
        by_id = {n["id"]: n for n in graph["nodes"]}
        ids = [n["id"] for n in graph["nodes"]]
        code = by_id["s-code-agents"]
        graphs = by_id["s-agent-graphs"]
        self.assertEqual(code["stage"], 3)
        self.assertEqual(code["rail"], "practice")
        self.assertEqual(code["prereqs"], ["s-ml-do"])
        self.assertEqual(graphs["stage"], 3)
        self.assertEqual(graphs["rail"], "practice")
        self.assertEqual(graphs["prereqs"], ["s-code-agents"])
        self.assertGreater(ids.index("s-code-agents"), ids.index("s-ml-do"))
        self.assertGreater(ids.index("s-code-agents"), ids.index("s-eval"))
        self.assertGreater(ids.index("s-code-agents"), ids.index("s-gnn"))
        self.assertTrue(code["do"])
        self.assertTrue(graphs["do"])

    def test_given_compiled_catalog_when_read_then_builder_urls_are_on_rails(self):
        resources = json.loads((ROOT / "data" / "resources.json").read_text())
        graph = json.loads((ROOT / "data" / "graph.json").read_text())
        by_id = {r["id"]: r for r in resources}
        rail_ids = set()
        for n in graph["nodes"]:
            if n["id"] in {"s-code-agents", "s-agent-graphs"}:
                for rail in ("do", "parallel", "skim", "project"):
                    rail_ids.update(n.get(rail) or [])
        blob = " ".join(
            f'{by_id[i]["title"]} {by_id[i]["url"]} {by_id[i].get("evidence","")}'
            for i in rail_ids
            if i in by_id
        ).lower()
        for needle in (
            "claude",
            "langgraph",
            "langchain",
            "cursor",
            "mcp",
            "autogen",
            "multi-agent",
        ):
            self.assertIn(needle, blob, msg=f"missing {needle} on builder rails")
        primary = next(n["do"][0] for n in graph["nodes"] if n["id"] == "s-code-agents")
        self.assertTrue(by_id[primary].get("sitting"))
        self.assertTrue(by_id[primary].get("scores"))
