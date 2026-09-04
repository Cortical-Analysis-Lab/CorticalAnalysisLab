#!/usr/bin/env python3
"""Small regression suite for the seed architecture."""

import json
import sqlite3
import subprocess
import sys
import tempfile
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
        self.assertGreaterEqual(self.count("opportunities"), 706)
        self.assertGreaterEqual(self.count("program_cycles"), 706)
        self.assertGreaterEqual(self.count("institutions"), 337)

    def test_every_cycle_has_eligibility(self):
        missing = self.db.execute("SELECT COUNT(*) FROM program_cycles c LEFT JOIN eligibility_rules e USING(cycle_id) WHERE e.cycle_id IS NULL").fetchone()[0]
        self.assertEqual(missing, 0)

    def test_unknowns_are_not_coerced_to_zero(self):
        row = self.db.execute("SELECT stipend_total_usd FROM program_cycles WHERE stipend_total_usd IS NULL LIMIT 1").fetchone()
        self.assertIsNotNone(row)

    def test_public_catalog_matches_database(self):
        payload = json.loads((ROOT / "data" / "summer-research" / "catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(len(payload["opportunities"]), self.count("opportunities"))
        self.assertEqual(payload["schema_version"], "1.2.0")

    def test_discovery_protocol_tables_are_seeded(self):
        self.assertGreaterEqual(self.count("discovery_sources"), 25)
        self.assertEqual(self.count("opportunity_discovery"), 0)
        self.assertEqual(self.count("crawl_targets"), 0)
        passes = {
            row[0]: row[1]
            for row in self.db.execute(
                "SELECT discovery_pass, COUNT(*) FROM discovery_sources GROUP BY discovery_pass"
            )
        }
        self.assertTrue({1, 2, 3, 4, 5}.issubset(passes))

    def test_research_modes_are_controlled_and_exported(self):
        self.assertEqual(self.count("research_modes"), 11)
        self.assertGreater(self.count("opportunity_research_modes"), 0)
        payload = json.loads((ROOT / "data" / "summer-research" / "catalog.json").read_text(encoding="utf-8"))
        self.assertTrue(all("research_modes" in item for item in payload["opportunities"]))

    def test_program_urls_are_preserved_for_public_catalog(self):
        missing = self.db.execute("SELECT COUNT(*) FROM opportunities WHERE program_url IS NULL").fetchone()[0]
        self.assertEqual(missing, 0)

    def test_csv_seed_round_trip_matches_committed_json(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            database = temporary / "catalog.sqlite"
            output = temporary / "export"
            subprocess.run([
                sys.executable, ROOT / "scripts" / "import_catalog.py",
                ROOT / "database" / "imports" / "summer_undergraduate_research_opportunities_starter.csv",
                "--database", database,
            ], cwd=ROOT, check=True, capture_output=True, text=True)
            subprocess.run([
                sys.executable, ROOT / "scripts" / "export_catalog.py",
                "--database", database, "--output", output,
            ], cwd=ROOT, check=True, capture_output=True, text=True)
            for generated in sorted(output.glob("*.json")):
                committed = ROOT / "data" / "summer-research" / generated.name
                self.assertEqual(
                    json.loads(generated.read_text(encoding="utf-8")),
                    json.loads(committed.read_text(encoding="utf-8")),
                    generated.name,
                )


if __name__ == "__main__":
    unittest.main()
