#!/usr/bin/env python3
"""Small regression suite for the seed architecture."""

import csv
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from catalog_common import (
    DEFAULT_DB, ROOT, disallowed_verification_source,
    eligibility_source_matches_official_program, is_funding_identity_url, load_rows,
)
from audit_catalog_accuracy import audit_rows
from apply_duplicate_identity_review import apply_review
from remove_funding_identity_records import remove_funding_identity_rows
from review_duplicate_identities import build_review_rows


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
        self.assertGreaterEqual(self.count("opportunities"), 35)
        self.assertGreaterEqual(self.count("program_cycles"), 35)
        self.assertGreaterEqual(self.count("institutions"), 33)

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

    def test_reviewed_eligibility_records_are_sourced(self):
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
        self.assertEqual(len(rows), self.count("opportunities"))
        for public_id, parse_status, has_source in rows:
            if parse_status == "reviewed":
                self.assertEqual(has_source, 1, public_id)
            else:
                self.assertEqual(parse_status, "needs_review", public_id)

    def test_funding_identity_urls_are_not_canonical_records(self):
        rows = self.db.execute("""
            SELECT o.public_id, o.program_url, o.application_url
            FROM opportunities o
            ORDER BY o.public_id
        """).fetchall()
        offenders = [
            f"{public_id}: {program_url or application_url}"
            for public_id, program_url, application_url in rows
            if is_funding_identity_url(program_url) or is_funding_identity_url(application_url)
        ]
        self.assertEqual(offenders, [])
        funding_sources = self.db.execute(
            "SELECT COUNT(*) FROM sources WHERE source_type='government_award' OR source_url LIKE '%awardsearch/showAward%'"
        ).fetchone()[0]
        self.assertEqual(funding_sources, 0)

    def test_unknowns_are_not_coerced_to_zero(self):
        row = self.db.execute("SELECT stipend_total_usd FROM program_cycles WHERE stipend_total_usd IS NULL LIMIT 1").fetchone()
        self.assertIsNotNone(row)

    def test_social_and_aggregator_pages_cannot_verify_catalog_fields(self):
        for url in (
            "https://www.instagram.com/example-program/",
            "https://linkedin.com/posts/example-program",
            "https://www.pathwaystoscience.org/programhub.aspx",
            "https://par.nsf.gov/biblio/1234567",
            "https://www.nsf.gov/awardsearch/showAward?AWD_ID=1234567",
            "https://reporter.nih.gov/project-details/123456",
            "https://example.edu/news/journal-article/example",
            "https://surf.rutgers.edu/outcomes/surf-to-jgpt-journey/",
            "https://fellowships.missouri.edu/fellowship/amgen-scholars/",
        ):
            self.assertTrue(disallowed_verification_source(url), url)

    def test_canonical_program_urls_do_not_use_discovery_only_pages(self):
        rows = self.db.execute(
            "SELECT public_id, program_url FROM opportunities ORDER BY public_id"
        ).fetchall()
        offenders = [
            f"{public_id}: {program_url}"
            for public_id, program_url in rows
            if disallowed_verification_source(program_url)
        ]
        self.assertEqual(offenders, [])

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

    def test_funding_identity_cleanup_removes_award_rows(self):
        headers = list(load_rows(ROOT / "database" / "imports" / "summer_undergraduate_research_opportunities_starter.csv")[0])
        official = {key: "" for key in headers}
        official.update({
            "Program_ID": "OFFICIAL-1",
            "Program_Name": "Official Summer Research Program",
            "Host_Institution": "Example University",
            "Primary_Field": "Multidisciplinary",
            "Cycle_Year": "2027",
            "Program_URL": "https://example.edu/summer-research",
            "Last_Verified": "2026-09-15",
        })
        funding = dict(official)
        funding.update({
            "Program_ID": "FUNDING-1",
            "Program_URL": "https://www.nsf.gov/awardsearch/showAward?AWD_ID=123",
            "Eligibility_Checked_By": "automated_nsf_metadata",
        })
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            import_path = tmpdir / "import.csv"
            output_path = tmpdir / "removed.csv"
            summary_path = tmpdir / "removed.md"
            with import_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
                writer.writeheader()
                writer.writerows([official, funding])
            report = remove_funding_identity_rows(import_path, output_path, summary_path)
            kept = load_rows(import_path)
        self.assertEqual(report["rows_removed"], 1)
        self.assertEqual([row["Program_ID"] for row in kept], ["OFFICIAL-1"])

    def test_public_catalog_matches_database(self):
        payload = json.loads((ROOT / "data" / "summer-research" / "catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(len(payload["opportunities"]), self.count("opportunities"))
        self.assertEqual(payload["schema_version"], "1.2.0")

    def test_discovery_protocol_tables_are_seeded(self):
        self.assertGreaterEqual(self.count("discovery_sources"), 25)
        self.assertEqual(self.count("opportunity_discovery"), 0)
        self.assertEqual(self.count("crawl_targets"), 0)
        grant_sources = self.db.execute(
            "SELECT COUNT(*) FROM discovery_sources WHERE source_type='grant_database'"
        ).fetchone()[0]
        self.assertEqual(grant_sources, 0)
        passes = {
            row[0]: row[1]
            for row in self.db.execute(
                "SELECT discovery_pass, COUNT(*) FROM discovery_sources GROUP BY discovery_pass"
            )
        }
        self.assertTrue({1, 2, 3, 5}.issubset(passes))

    def test_research_modes_are_controlled_and_exported(self):
        self.assertEqual(self.count("research_modes"), 11)
        self.assertGreater(self.count("opportunity_research_modes"), 0)
        payload = json.loads((ROOT / "data" / "summer-research" / "catalog.json").read_text(encoding="utf-8"))
        self.assertTrue(all("research_modes" in item for item in payload["opportunities"]))

    def test_neuroscience_is_a_first_class_research_area(self):
        primary_rows = self.db.execute("""
            SELECT COUNT(*)
            FROM opportunities o
            JOIN opportunity_categories oc USING(opportunity_id)
            JOIN research_categories rc USING(category_id)
            WHERE rc.category_name='Neuroscience & Cognitive Science'
              AND oc.is_primary=1
        """).fetchone()[0]
        all_rows = self.db.execute("""
            SELECT COUNT(*)
            FROM opportunities o
            JOIN opportunity_categories oc USING(opportunity_id)
            JOIN research_categories rc USING(category_id)
            WHERE rc.category_name='Neuroscience & Cognitive Science'
        """).fetchone()[0]
        self.assertGreaterEqual(primary_rows, 2)
        self.assertGreaterEqual(all_rows, primary_rows)
        specific = self.db.execute("""
            SELECT COUNT(*)
            FROM opportunities o
            JOIN opportunity_categories oc USING(opportunity_id)
            JOIN research_categories rc USING(category_id)
            WHERE o.public_id IN ('AUTO-5F1B08398C', 'UCONN-PNB-REU')
              AND rc.category_name='Neuroscience & Cognitive Science'
              AND oc.is_primary=1
        """).fetchone()[0]
        self.assertEqual(specific, 2)

    def test_accuracy_audit_flags_award_only_rows(self):
        rows = [{
            "Program_ID": "NSF-REU-123",
            "Program_Name": "Research Experiences for Undergraduates in Example Science",
            "Host_Institution": "Example University",
            "Program_URL": "https://www.nsf.gov/awardsearch/showAward?AWD_ID=123",
            "Application_URL": "https://www.nsf.gov/awardsearch/showAward?AWD_ID=123",
            "Cycle_Year": "2029",
            "Duration_Weeks": "N/A",
            "Program_Start": "N/A",
            "Program_End": "N/A",
            "Application_Open": "N/A",
            "Application_Deadline": "N/A",
            "Stipend_Total_USD": "N/A",
            "Stipend_Weekly_USD": "N/A",
            "Eligibility_Parse_Status": "reviewed",
            "Eligibility_Checked_By": "automated_nsf_metadata",
        }]
        codes = {finding["Issue_Code"] for finding in audit_rows(rows)}
        self.assertIn("award_metadata_only", codes)
        self.assertIn("award_url_used_as_application", codes)
        self.assertIn("award_only_eligibility_marked_reviewed", codes)

    def test_duplicate_identity_review_prefers_stronger_official_row(self):
        rows = [
            {
                "Program_ID": "PROGRAM-OLD",
                "Program_Name": "Example REU",
                "Host_Institution": "Example University",
                "Cycle_Year": "2027",
                "Data_Confidence": "Low",
                "Program_URL": "https://example.edu/reu/archive",
                "Application_URL": "",
            },
            {
                "Program_ID": "PROGRAM-CURRENT",
                "Program_Name": "Example REU",
                "Host_Institution": "Example University",
                "Cycle_Year": "2029",
                "Data_Confidence": "High",
                "Program_URL": "https://example.edu/reu",
                "Application_URL": "https://example.edu/reu/apply",
            },
        ]
        review = build_review_rows(rows)
        self.assertEqual(len(review), 2)
        self.assertTrue(all(row["Recommended_Action"] == "review_same_program_multiple_pages" for row in review))
        keep_rows = [row for row in review if row["Recommendation"] == "keep"]
        self.assertEqual(keep_rows[0]["Program_ID"], "PROGRAM-CURRENT")

    def test_apply_duplicate_identity_review_removes_duplicates_and_logs_merge(self):
        import tempfile
        headers = [
            "Program_ID", "Program_Name", "Host_Institution", "Network_Source",
            "Program_Type", "Primary_Field", "Field_Tags", "City", "State",
            "Country", "Location_Scope", "Format", "External_Applicants",
            "Citizenship", "Eligible_Years", "Min_GPA", "Duration_Weeks",
            "Program_Start", "Program_End", "Application_Open",
            "Application_Deadline", "Deadline_Text", "Cycle_Year", "Status",
            "Stipend_Total_USD", "Stipend_Weekly_USD", "Housing_Included",
            "Housing_Details", "Meals_Included", "Meals_Details",
            "Travel_Included", "Travel_Details", "Academic_Credit",
            "Program_URL", "Application_URL", "Last_Verified",
            "Data_Confidence", "Notes", "Eligibility_Parse_Status",
            "Citizenship_US_Citizen", "Citizenship_Permanent_Resident",
            "Citizenship_International", "First_Year_Eligible",
            "Sophomore_Eligible", "Junior_Eligible", "Senior_Eligible",
            "Graduating_Senior_Eligible", "Enrolled_Required",
            "Graduation_Rule_Text", "Institution_Type_Rule_Text",
            "Two_Year_Institution_Eligible", "Four_Year_Institution_Eligible",
            "Degree_Seeking_Required", "Prior_Research_Status",
            "Raw_Eligibility_Text", "Other_Rule_Text",
            "Eligibility_Source_URL", "Eligibility_Checked_On",
            "Eligibility_Checked_By",
        ]
        rows = []
        for public_id, year, url in (
            ("PROGRAM-OLD", "2027", "https://example.edu/reu/archive"),
            ("PROGRAM-CURRENT", "2029", "https://example.edu/reu"),
        ):
            row = {key: "" for key in headers}
            row.update({
                "Program_ID": public_id,
                "Program_Name": "Example REU",
                "Host_Institution": "Example University",
                "Cycle_Year": year,
                "Program_URL": url,
                "Data_Confidence": "Low",
            })
            rows.append(row)
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            import_path = tmpdir / "import.csv"
            review_path = tmpdir / "review.csv"
            log_path = tmpdir / "log.csv"
            summary_path = tmpdir / "log.md"
            with import_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            review = build_review_rows(rows)
            with review_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(review[0]), lineterminator="\n")
                writer.writeheader()
                writer.writerows(review)
            report = apply_review(import_path, review_path, log_path, summary_path)
            updated_rows = load_rows(import_path)
        self.assertEqual(report["rows_removed"], 1)
        self.assertEqual([row["Program_ID"] for row in updated_rows], ["PROGRAM-CURRENT"])
        self.assertIn("PROGRAM-OLD", updated_rows[0]["Notes"])
        self.assertNotIn("award", updated_rows[0]["Notes"].lower())

    def test_discovery_protocol_is_broad_and_excludes_grant_databases(self):
        source_catalog = json.loads((ROOT / "database" / "discovery" / "source_catalog_seed.json").read_text(encoding="utf-8"))
        host_protocol = json.loads((ROOT / "database" / "discovery" / "host_universe_protocol.json").read_text(encoding="utf-8"))
        source_types = {row["source_type"] for row in source_catalog}
        self.assertNotIn("grant_database", source_types)
        text = json.dumps(host_protocol).lower()
        for term in ("neuroscience", "cognitive", "biology", "chemistry", "engineering", "public health", "physics"):
            self.assertIn(term, text)

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
