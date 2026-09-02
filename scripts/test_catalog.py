#!/usr/bin/env python3
"""Small regression suite for the seed architecture."""

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from catalog_common import (
    DEFAULT_DB, ROOT, disallowed_verification_source,
    eligibility_source_matches_official_program,
)
from catalog_staging import add_manual_links, candidate_counts, list_candidates, set_review_status
from run_discovery_session import classify_candidate, deduplicate, nsf_awards


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

    def test_reviewed_amgen_eligibility_is_structured(self):
        rows = self.db.execute("""
            SELECT o.public_id, e.parse_status, e.citizenship_us_citizen,
                   e.citizenship_permanent_resident, e.citizenship_international,
                   e.first_year_eligible, e.sophomore_eligible, e.junior_eligible,
                   e.senior_eligible, e.graduating_senior_eligible,
                   e.two_year_institution_eligible, e.four_year_institution_eligible
            FROM opportunities o
            JOIN program_cycles c USING(opportunity_id)
            JOIN eligibility_rules e USING(cycle_id)
            WHERE o.public_id IN ('AMGEN-HARV', 'AMGEN-STAN', 'AMGEN-UCB')
        """).fetchall()
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertEqual(row[1:], ("reviewed", 1, 1, 0, 0, 1, 1, 1, 0, 0, 1), row[0])

    def test_every_eligibility_record_is_reviewed_and_sourced(self):
        rows = self.db.execute("""
            SELECT o.public_id, e.parse_status,
                   EXISTS (
                       SELECT 1
                       FROM source_verifications v
                       WHERE v.cycle_id = c.cycle_id
                         AND v.verification_status = 'verified'
                         AND v.fields_supported LIKE '%eligibility%'
                   ) AS has_verified_eligibility_source
            FROM opportunities o
            JOIN program_cycles c USING(opportunity_id)
            JOIN eligibility_rules e USING(cycle_id)
            ORDER BY o.public_id
        """).fetchall()
        self.assertEqual(len(rows), 35)
        for public_id, parse_status, has_source in rows:
            self.assertEqual(parse_status, "reviewed", public_id)
            self.assertEqual(has_source, 1, public_id)

    def test_unknowns_are_not_coerced_to_zero(self):
        row = self.db.execute("SELECT stipend_total_usd FROM program_cycles WHERE stipend_total_usd IS NULL LIMIT 1").fetchone()
        self.assertIsNotNone(row)

    def test_social_and_aggregator_pages_cannot_verify_catalog_fields(self):
        for url in (
            "https://www.instagram.com/example-program/",
            "https://linkedin.com/posts/example-program",
            "https://www.pathwaystoscience.org/programhub.aspx",
        ):
            self.assertTrue(disallowed_verification_source(url), url)

    def test_eligibility_source_must_share_reviewed_official_domain_family(self):
        program = "https://reu.dimacs.rutgers.edu/"
        self.assertTrue(eligibility_source_matches_official_program(
            "https://dimacs.rutgers.edu/apply-to-the-dimacs-reu", program
        ))
        self.assertFalse(eligibility_source_matches_official_program(
            "https://www.reddit.com/r/reu/comments/example", program
        ))
        self.assertFalse(eligibility_source_matches_official_program(
            "https://third-party-example.org/dimacs", program
        ))

    def test_discovery_matches_canonical_identity_before_deep_verification(self):
        catalog = [{
            "public_id": "DIMACS-REU", "program_name": "DIMACS REU",
            "institution_name": "Rutgers University-New Brunswick", "program_url": "https://dimacs.rutgers.edu/",
        }]
        state, public_id, _ = classify_candidate(
            "REU Site: DIMACS REU", "Rutgers University-New Brunswick", catalog
        )
        self.assertEqual((state, public_id), ("EXISTING_PROGRAM", "DIMACS-REU"))
        state, public_id, _ = classify_candidate(
            "REU Site: A New Ocean Science Program", "Example University", catalog
        )
        self.assertEqual((state, public_id), ("NEW_PROGRAM", ""))

    def test_nsf_discovery_payload_and_duplicate_awards_are_normalized(self):
        payload = {"response": {"award": {"id": "123", "title": "REU Site: Example"}, "metadata": [{"totalCount": "1"}]}}
        awards, total = nsf_awards(payload)
        self.assertEqual((len(awards), total), (1, 1))
        candidate = {
            "candidate_id": "NSF-123", "discovery_source": "source-a",
            "match_state": "NEW_PROGRAM", "institution_observed": "Example", "program_name_observed": "Example",
        }
        duplicate = dict(candidate, discovery_source="source-b")
        rows = deduplicate([candidate, duplicate])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["discovery_source"], "source-a;source-b")

    def test_local_staging_persists_manual_links_and_review_state(self):
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory) / "candidates.sqlite"
            first = add_manual_links(
                ["https://example.edu/research/summer#details"],
                "User supplied", staging,
            )
            second = add_manual_links(
                ["https://example.edu/research/summer"],
                "Seen again", staging,
            )
            self.assertEqual(first, second)
            self.assertEqual(candidate_counts(staging)["total"], 1)
            set_review_status(first[0], "investigating", staging)
            row = list_candidates(staging)[0]
            self.assertEqual(row["review_status"], "investigating")
            self.assertEqual(row["normalized_url"], "https://example.edu/research/summer")

    def test_public_catalog_matches_database(self):
        payload = json.loads((ROOT / "data" / "summer-research" / "catalog.json").read_text())
        self.assertEqual(len(payload["opportunities"]), self.count("opportunities"))
        self.assertEqual(payload["schema_version"], "1.1.0")

    def test_research_modes_are_controlled_and_exported(self):
        self.assertEqual(self.count("research_modes"), 11)
        self.assertGreater(self.count("opportunity_research_modes"), 0)
        payload = json.loads((ROOT / "data" / "summer-research" / "catalog.json").read_text())
        self.assertTrue(all("research_modes" in item for item in payload["opportunities"]))

    def test_application_urls_are_preserved_per_cycle(self):
        missing = self.db.execute("SELECT COUNT(*) FROM program_cycles WHERE application_url IS NULL").fetchone()[0]
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
                self.assertEqual(json.loads(generated.read_text()), json.loads(committed.read_text()), generated.name)


if __name__ == "__main__":
    unittest.main()
