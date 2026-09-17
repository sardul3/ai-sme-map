import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from focus import apply_status, do_ids_for_station, is_complete, next_focus, rollup_all


GRAPH = {
    "nodes": [
        {"id": "s-a", "title": "See matrices", "stage": 0, "do": ["r-3b1b"]},
        {"id": "s-b", "title": "Work matrices", "stage": 0, "do": ["r-imperial", "r-strang"]},
        {"id": "s-c", "title": "Later", "stage": 2, "do": ["r-later"]},
    ]
}

RES = [
    {
        "id": "r-3b1b",
        "title": "Essence of Linear Algebra",
        "url": "https://3blue1brown.com/topics/linear-algebra",
        "sitting": "~3 h",
        "parts": [
            {"id": "r-3b1b:vectors", "title": "Vectors", "url": "https://3blue1brown.com/lessons/vectors"},
            {"id": "r-3b1b:span", "title": "Span", "url": "https://3blue1brown.com/lessons/span"},
        ],
    },
    {
        "id": "r-imperial",
        "title": "Imperial LA",
        "url": "https://coursera.org/learn/linear-algebra-machine-learning",
        "sitting": "~4 h (week 1)",
        "parts": [
            {"id": "r-imperial:week-1", "title": "Week 1", "url": None},
            {"id": "r-imperial:week-2", "title": "Week 2", "url": None},
        ],
    },
    {"id": "r-strang", "title": "18.06", "url": "https://ocw.mit.edu/18-06", "sitting": "~3 h"},
    {"id": "r-later", "title": "Year 2 paper", "url": "https://example.com/later", "sitting": "~2 h"},
]
RES.append({"id": "r-extra", "title": "Pinned extra", "url": "https://example.com/extra-course", "sitting": "~1 h"})


def by_id(resources):
    return {r["id"]: r for r in resources}


class TestNextFocus(unittest.TestCase):
    def test_empty_progress_is_first_unfinished_part(self):
        f = next_focus(GRAPH, RES, {})
        self.assertEqual(f["station_id"], "s-a")
        self.assertEqual(f["resource_id"], "r-3b1b")
        self.assertEqual(f["part_id"], "r-3b1b:vectors")
        self.assertIn("Vectors", f["label"])
        self.assertFalse(f["done"])

    def test_completing_primary_advances_station_even_if_later_do_open(self):
        f = next_focus(GRAPH, RES, {"r-3b1b": "done", "r-imperial": "done"})
        self.assertEqual(f["station_id"], "s-c")
        self.assertEqual(f["resource_id"], "r-later")

    def test_doing_is_not_complete(self):
        f = next_focus(GRAPH, RES, {"r-3b1b:vectors": "doing"})
        self.assertEqual(f["part_id"], "r-3b1b:vectors")


class TestParts(unittest.TestCase):
    def test_parent_done_covers_parts(self):
        bid = by_id(RES)
        self.assertTrue(is_complete({"r-3b1b": "done"}, "r-3b1b:vectors", bid))
        f = next_focus(GRAPH, RES, {"r-3b1b": "done"})
        self.assertEqual(f["resource_id"], "r-imperial")

    def test_all_parts_done_completes_parent(self):
        progress = {"r-3b1b:vectors": "done", "r-3b1b:span": "done"}
        self.assertTrue(is_complete(progress, "r-3b1b", by_id(RES)))

    def test_mark_parent_done_writes_parts(self):
        out = apply_status({}, by_id(RES), "r-3b1b", "done")
        self.assertEqual(out["r-3b1b"], "done")
        self.assertEqual(out["r-3b1b:vectors"], "done")

    def test_unchecking_part_uncompletes_parent(self):
        start = apply_status({}, by_id(RES), "r-3b1b", "done")
        out = apply_status(start, by_id(RES), "r-3b1b:span", "todo")
        self.assertEqual(out["r-3b1b"], "doing")

    def test_last_part_marks_parent(self):
        out = apply_status({"r-3b1b:vectors": "done"}, by_id(RES), "r-3b1b:span", "done")
        self.assertEqual(out["r-3b1b"], "done")

    def test_rollup_parent_done_fills_parts(self):
        out = rollup_all({"r-3b1b": "done"}, by_id(RES))
        self.assertEqual(out["r-3b1b:span"], "done")


class TestPins(unittest.TestCase):
    def test_given_pin_when_focus_then_pinned_resource(self):
        f = next_focus(GRAPH, RES, {"pins": {"s-a": "r-extra"}})
        self.assertEqual(f["station_id"], "s-a")
        self.assertEqual(f["resource_id"], "r-extra")
        self.assertIsNone(f["part_id"])

    def test_given_pin_done_when_focus_then_compiled_do0(self):
        f = next_focus(GRAPH, RES, {"pins": {"s-a": "r-extra"}, "r-extra": "done"})
        self.assertEqual(f["resource_id"], "r-3b1b")
        self.assertEqual(f["part_id"], "r-3b1b:vectors")

    def test_given_unknown_pin_when_focus_then_compiled_do0(self):
        f = next_focus(GRAPH, RES, {"pins": {"s-a": "r-missing"}})
        self.assertEqual(f["resource_id"], "r-3b1b")

    def test_given_later_station_pin_when_earlier_open_then_stay(self):
        f = next_focus(GRAPH, RES, {"pins": {"s-c": "r-extra"}})
        self.assertEqual(f["station_id"], "s-a")
        self.assertEqual(f["resource_id"], "r-3b1b")

    def test_given_pin_with_parts_when_focus_then_first_part(self):
        f = next_focus(GRAPH, RES, {"pins": {"s-b": "r-imperial"}, "r-3b1b": "done"})
        self.assertEqual(f["station_id"], "s-b")
        self.assertEqual(f["resource_id"], "r-imperial")
        self.assertEqual(f["part_id"], "r-imperial:week-1")

    def test_do_ids_put_pin_first_without_duplicate(self):
        from focus import by_id

        ids = do_ids_for_station(GRAPH["nodes"][0], {"pins": {"s-a": "r-extra"}}, by_id(RES))
        self.assertEqual(ids[0], "r-extra")
        self.assertEqual(ids[1], "r-3b1b")
        self.assertEqual(len(ids), 2)


class TestVotes(unittest.TestCase):
    def test_given_upvote_when_apply_then_stored(self):
        from focus import apply_vote, vote_of, votes_of

        out = apply_vote({}, "r-3b1b", 1)
        self.assertEqual(vote_of(out, "r-3b1b"), 1)
        self.assertEqual(votes_of(out)["r-3b1b"], 1)

    def test_given_same_vote_when_apply_again_then_cleared(self):
        from focus import apply_vote, vote_of

        once = apply_vote({}, "r-3b1b", 1)
        out = apply_vote(once, "r-3b1b", 1)
        self.assertEqual(vote_of(out, "r-3b1b"), 0)
        self.assertNotIn("r-3b1b", out.get("votes") or {})

    def test_given_upvote_when_downvote_then_switches(self):
        from focus import apply_vote, vote_of

        out = apply_vote(apply_vote({}, "r-3b1b", 1), "r-3b1b", -1)
        self.assertEqual(vote_of(out, "r-3b1b"), -1)

    def test_given_votes_when_status_then_votes_survive(self):
        from focus import apply_status, apply_vote

        start = apply_vote({}, "r-3b1b", 1)
        out = apply_status(start, by_id(RES), "r-imperial", "done")
        self.assertEqual(out["votes"]["r-3b1b"], 1)
        self.assertEqual(out["r-imperial"], "done")

    def test_given_votes_when_focus_then_still_do0(self):
        f = next_focus(GRAPH, RES, {"votes": {"r-strang": 1, "r-3b1b": -1}})
        self.assertEqual(f["resource_id"], "r-3b1b")


class TestCatalogFocus(unittest.TestCase):
    def test_empty_atlas_focuses_essence_path(self):
        import json

        root = Path(__file__).resolve().parents[1]
        graph = json.loads((root / "data" / "graph.json").read_text())
        resources = json.loads((root / "data" / "resources.json").read_text())
        f = next_focus(graph, resources, {})
        self.assertFalse(f["done"])
        self.assertIn("Essence", f.get("resource_title") or f.get("label") or "")


if __name__ == "__main__":
    unittest.main()
