# tests/test_assignments.py
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from assignments import apply_placements, validate_assignments
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
