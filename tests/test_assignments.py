# tests/test_assignments.py
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from assignments import apply_placements, filter_placements, validate_assignments
from library import unassigned


def nodes():
    return [
        {
            "id": "s-a",
            "do": ["r-seed"],
            "parallel": [],
            "skim": [],
            "project": [],
        }
    ]


class TestFilterPlacements(unittest.TestCase):
    def test_given_mixed_ids_when_filtered_then_keeps_known_drops_unknown(self):
        placements = {
            "r-known": {"station": "s-a", "rail": "parallel"},
            "r-unknown": {"station": "s-a", "rail": "do"},
            "r-tomb": None,
        }
        known = {"r-known", "r-seed"}
        out = filter_placements(placements, known)
        self.assertEqual(set(out.keys()), {"r-known"})
        self.assertEqual(out["r-known"]["rail"], "parallel")

    def test_given_filtered_placements_when_merged_then_unknown_not_on_rails(self):
        known_ids = {"r-seed", "r-known"}
        placements = filter_placements(
            {
                "r-known": {"station": "s-a", "rail": "parallel"},
                "r-unknown": {"station": "s-a", "rail": "do"},
            },
            known_ids,
        )
        out = apply_placements(nodes(), placements)
        st = out[0]
        all_rail_ids = set(st["do"]) | set(st["parallel"]) | set(st["skim"]) | set(st["project"])
        self.assertIn("r-known", st["parallel"])
        self.assertNotIn("r-unknown", all_rail_ids)


class TestApplyPlacements(unittest.TestCase):
    def test_given_missing_key_when_merged_then_seed_kept(self):
        out = apply_placements(nodes(), {})
        self.assertEqual(out[0]["do"], ["r-seed"])

    def test_given_placement_when_merged_then_moves_to_rail(self):
        out = apply_placements(nodes(), {"r-harvest": {"station": "s-a", "rail": "parallel"}})
        self.assertIn("r-harvest", out[0]["parallel"])
        self.assertEqual(out[0]["do"], ["r-seed"])

    def test_given_tombstone_when_merged_then_stripped_from_seed(self):
        out = apply_placements(nodes(), {"r-seed": None})
        self.assertEqual(out[0]["do"], [])

    def test_given_move_when_merged_then_not_duplicated(self):
        out = apply_placements(nodes(), {"r-seed": {"station": "s-a", "rail": "skim"}})
        self.assertEqual(out[0]["do"], [])
        self.assertEqual(out[0]["skim"], ["r-seed"])

    def test_given_unknown_station_when_merged_then_skipped(self):
        out = apply_placements(nodes(), {"r-x": {"station": "s-nope", "rail": "do"}})
        self.assertEqual(out[0]["do"], ["r-seed"])

    def test_given_unknown_station_for_seed_when_merged_then_seed_kept(self):
        out = apply_placements(nodes(), {"r-seed": {"station": "s-nope", "rail": "do"}})
        self.assertEqual(out[0]["do"], ["r-seed"])

    def test_given_bad_rail_when_validated_then_error(self):
        errs = validate_assignments(
            {"schema_version": 1, "placements": {"r-x": {"station": "s-a", "rail": "must"}}}
        )
        self.assertTrue(errs)

    def test_given_placement_when_unassigned_then_not_library(self):
        resources = [
            {"id": "r-seed", "title": "Seed", "url": "https://ex.com/s", "source": "curated"},
            {"id": "r-harvest", "title": "H", "url": "https://ex.com/h", "source": "awesome-ml.md"},
        ]
        graph = {"nodes": apply_placements(nodes(), {"r-harvest": {"station": "s-a", "rail": "parallel"}})}
        ids = {r["id"] for r in unassigned(resources, graph)}
        self.assertNotIn("r-harvest", ids)
        self.assertNotIn("r-seed", ids)

    def test_given_tombstone_when_unassigned_then_library(self):
        resources = [{"id": "r-seed", "title": "Seed", "url": "https://ex.com/s", "source": "curated"}]
        graph = {"nodes": apply_placements(nodes(), {"r-seed": None})}
        ids = {r["id"] for r in unassigned(resources, graph)}
        self.assertEqual(ids, {"r-seed"})

    def test_given_compile_source_when_read_then_applies_placements(self):
        text = (Path(__file__).resolve().parents[1] / "scripts" / "compile_catalog.py").read_text()
        self.assertIn("apply_placements", text)
        self.assertIn("load_assignments", text)
        self.assertIn("graph.seed.json", text)
        self.assertIn("filter_placements", text)
