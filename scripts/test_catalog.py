#!/usr/bin/env python3
"""Small regression suite for the seed architecture."""

import json
import sqlite3
import unittest
from pathlib import Path

from catalog_common import DEFAULT_DB, ROOT


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = sqlite3.connect(DEFAULT_DB)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def count(self, table):
        return self.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def test_seed_counts(self):
        self.assertEqual(self.count("opportunities"), 35)
        self.assertEqual(self.count("program_cycles"), 35)
        self.assertEqual(self.count("institutions"), 33)

    def test_every_cycle_has_eligibility(self):
        missing = self.db.execute("SELECT COUNT(*) FROM program_cycles c LEFT JOIN eligibility_rules e USING(cycle_id) WHERE e.cycle_id IS NULL").fetchone()[0]
        self.assertEqual(missing, 0)

    def test_unknowns_are_not_coerced_to_zero(self):
        row = self.db.execute("SELECT stipend_total_usd FROM program_cycles WHERE stipend_total_usd IS NULL LIMIT 1").fetchone()
        self.assertIsNotNone(row)

    def test_public_catalog_matches_database(self):
        payload = json.loads((ROOT / "data" / "summer-research" / "catalog.json").read_text())
        self.assertEqual(len(payload["opportunities"]), self.count("opportunities"))
        self.assertEqual(payload["schema_version"], "1.0.0")


if __name__ == "__main__":
    unittest.main()
