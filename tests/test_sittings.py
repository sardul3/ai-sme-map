import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestBeginnerSittings(unittest.TestCase):
    def test_first_ten_unique_do_resources_declare_a_sitting(self):
        graph = json.loads((ROOT / "data" / "graph.json").read_text())
        resources = json.loads((ROOT / "data" / "resources.json").read_text())
        by_id = {r["id"]: r for r in resources}
        seen = []
        for node in graph["nodes"]:
            for rid in node.get("do") or []:
                if rid not in seen:
                    seen.append(rid)
                if len(seen) == 10:
                    break
            if len(seen) == 10:
                break
        self.assertEqual(len(seen), 10)
        missing = [by_id[i]["title"] for i in seen if not by_id[i].get("sitting")]
        self.assertEqual(missing, [], msg="first Do items need a sitting length")

    def test_first_sixty_unique_do_resources_have_scores(self):
        graph = json.loads((ROOT / "data" / "graph.json").read_text())
        resources = json.loads((ROOT / "data" / "resources.json").read_text())
        by_id = {r["id"]: r for r in resources}
        seen = []
        for node in graph["nodes"]:
            for rid in node.get("do") or []:
                if rid not in seen:
                    seen.append(rid)
                if len(seen) == 60:
                    break
            if len(seen) == 60:
                break
        missing = [by_id[i]["title"] for i in seen if not by_id[i].get("scores")]
        self.assertEqual(missing, [])
