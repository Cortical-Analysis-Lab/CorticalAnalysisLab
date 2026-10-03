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
from review_catalog_names import apply_decisions, canonical_url, clean_name, screen
from import_catalog import preflight


class CatalogTests(unittest.TestCase):
    def test_october_review_preserves_identity_and_cycle_boundaries(self):
        payload = json.loads((ROOT / "data/summer-research/catalog.json").read_text())
        programs = {p["public_id"]: p for p in payload["opportunities"]}
        self.assertEqual(len(programs), 1031)

        def cycle(pid, year=2027):
            return next(c for c in programs[pid]["cycles"] if c["cycle_year"] == year)

        self.assertEqual(cycle("NIH-SIP")["application_deadline"], "2027-01-26")
        self.assertEqual(cycle("NASA-OSTEM")["application_deadline"], "2027-03-01")
        self.assertEqual(cycle("hs:bu-rise")["application_deadline"], "2027-02-03")
        self.assertEqual(cycle("hs:stjude-hsri")["program_start"], "2027-06-01")
        self.assertEqual(programs["hs:stjude-hsri"]["high_school_details"]["cycles"][0]["start"], "2027-06-01")
        self.assertIsNone(cycle("hs:upmc-hillman")["program_start"])
        self.assertIn("tentative", cycle("hs:upmc-hillman")["deadline_text"])
        self.assertIsNone(programs["BND-45771DA7A83402F3"]["program_url"])

        # A deadline-only new cycle does not inherit 2026 benefit promises or
        # eligibility exclusions. Non-USD/daily/hourly reports stay narrative.
        amgen = cycle("AMGEN-UCB")
        self.assertIsNone(amgen["stipend_total_usd"])
        self.assertEqual(amgen["housing_status"], "unknown")
        self.assertEqual(amgen["eligibility"]["parse_status"], "needs_review")
        self.assertIsNone(amgen["eligibility"]["citizenship_international"])
        self.assertIsNone(amgen["last_verified"])
        self.assertEqual(cycle("AMGEN-UCB", 2026)["stipend_total_usd"], 5000)
        self.assertIsNone(cycle("BND-OIST")["stipend_total_usd"])
        self.assertIsNone(cycle("BND-1DC1462F04800634")["stipend_total_usd"])
        self.assertEqual(cycle("BND-ISTA-ISTERNSHIP")["status_code"], "closed")

    def test_complete_review_rejects_mismatches_and_preserves_unknowns(self):
        payload = json.loads((ROOT / "data/summer-research/catalog.json").read_text())
        programs = {p["public_id"]: p for p in payload["opportunities"]}

        def cycle(pid, year=2027):
            return next(c for c in programs[pid]["cycles"] if c["cycle_year"] == year)

        for pid in ("BND-730E888D56D253BE", "BND-AEC80FD7C401F158",
                    "AUTO-97DF9D9FCB", "AUTO-F44FD4F2FE"):
            self.assertNotIn(pid, programs)
        for pid in ("AUTO-5F1B08398C", "AUTO-ED34824776", "AUTO-943D64D03F"):
            self.assertFalse(any(c["cycle_year"] == 2027 for c in programs[pid]["cycles"]))
        self.assertIsNone(cycle("AUTO-862185FB01")["application_deadline"])
        self.assertIn("Priority deadline", cycle("AUTO-862185FB01")["deadline_text"])
        self.assertIsNone(cycle("BND-D06839A1D69FC89A")["application_deadline"])
        self.assertIn("tentative", cycle("BND-D06839A1D69FC89A")["deadline_text"])
        self.assertEqual(cycle("BND-C59E3E5A9114D68B")["status_code"], "closed")
        self.assertIsNone(cycle("BND-C59E3E5A9114D68B")["stipend_total_usd"])
        self.assertEqual(cycle("BND-AADC31FAA2BE4B83")["stipend_weekly_usd"], 680)
        self.assertIsNone(cycle("BND-AADC31FAA2BE4B83")["stipend_total_usd"])
        self.assertEqual(cycle("BND-0213B548E5D9362D")["application_open"], "2026-11-01")
        access = programs["BND-94E67026F1003A21"]
        self.assertTrue(access["program_url"].endswith("/capacity-building-programs/access"))
        self.assertFalse(any(c["cycle_year"] == 2027 for c in access["cycles"]))
        for pid in ("hs:ucsb-rmp", "hs:ucsb-sra"):
            details = programs[pid]["high_school_details"]
            latest = details["cycles"][0]
            self.assertEqual(latest["year"], 2027)
            self.assertEqual(latest["deadline"], cycle(pid)["application_deadline"])
            self.assertNotIn("commuterUSD", latest)
            self.assertEqual(latest["housing"], "unknown")
            self.assertEqual(latest["summerLinkedAid"]["status"], "unknown")
            self.assertTrue(any(c.get("commuterUSD") for c in details["cycles"] if c["year"] == 2026))
        ledger = access["bundle_details"][0]["catalogCompleteReviewLedger"]
        self.assertIn("not exhaustive field verification", ledger["limitation"])

    def test_high_school_import_identity_and_audience(self):
        payload = json.loads((ROOT / "data/summer-research/catalog.json").read_text())
        programs = payload["opportunities"]
        high_school = [p for p in programs if p.get("high_school_details")]
        self.assertEqual(len(high_school), 89)
        self.assertEqual(len({p["high_school_details"]["id"] for p in high_school}), 89)
        self.assertEqual(sum(p["public_id"].startswith("hs:") for p in programs), 82)
        self.assertEqual(sum("Neuroscience" in p["high_school_details"]["researchAreas"] for p in high_school), 7)
        self.assertEqual(sum(p["high_school_details"]["summerLinkedAid"]["status"] == "available" for p in high_school), 17)
        for program in high_school:
            self.assertIn(program["catalog_audience"], ("high_school", "both"))
        shared = {p["public_id"] for p in high_school if not p["public_id"].startswith("hs:")}
        self.assertEqual(shared, {"NIH-SIP", "BND-9AA23EF5737E54EC", "BND-B83DAE59C761F92E", "AUTO-C1E6B2C256", "BND-3D2F2979986F74C6", "BND-331673672AEF2B91", "BND-66CEB010CAE9B467"})
        rows = load_rows(ROOT / "database/imports/summer_undergraduate_research_opportunities_starter.csv")
        invalid = dict(rows[0], Catalog_Audience="guessed")
        self.assertTrue(any("invalid Catalog_Audience" in error for error in preflight([invalid])[0]))

    def test_unresolved_review_preserves_tracks_and_corrects_scope(self):
        rows = load_rows(ROOT / "database/imports/summer_undergraduate_research_opportunities_starter.csv")
        programs = {r["Program_ID"]: r for r in rows}
        for excluded in ("BND-084EF69750C5A3D1", "AUTO-5BDE34CD1E", "BND-EF0857A517205E5A",
                         "BND-9247DF9AB8E522C6", "BND-CA3CDDC5738FE044", "AUTO-7F03609722"):
            self.assertNotIn(excluded, programs)
        # A WashU restriction must not exclude the separately represented Penn site.
        penn = programs["BND-21B2481861C524C2"]
        self.assertEqual(penn["Host_Institution"], "University of Pennsylvania")
        self.assertEqual(penn["External_Applicants"], "Unknown")
        self.assertEqual(penn["Housing_Included"], "Unknown")
        self.assertTrue(penn["Review_Notes"])
        # Broad SRTP must not inherit the Amgen funding track's GPA requirement.
        self.assertEqual(programs["AMGEN-UCSF"]["Min_GPA"], "")
        self.assertEqual(programs["AMGEN-UCSF"]["Eligibility_Parse_Status"], "needs_review")
        self.assertEqual(programs["AUTO-531D141B73"]["Stipend_Total_USD"], "6000")
        self.assertEqual(programs["BND-B79CDBD477F02CEB"]["Stipend_Total_USD"], "7000")
        for identity in ("AUTO-583E67E91D", "AUTO-6CDAF7E06A"):
            self.assertIn("cancelled", programs[identity]["Status"])
        self.assertEqual(programs["BND-4334627EF951B1D4"]["Program_URL"], "")
        self.assertFalse(programs["BND-4334627EF951B1D4"]["Source_Evidence_JSON"])

    def test_full_overlap_batch_and_test_name_exclusion(self):
        rows = load_rows(ROOT / "database/imports/summer_undergraduate_research_opportunities_starter.csv")
        by_id = {r["Program_ID"]: r for r in rows}
        self.assertFalse([r["Program_Name"] for r in rows if "test" in r["Program_Name"].lower()])
        for keep, removed in [
            ("BU-SURF", "BND-F16288E8ACDFB78B"),
            ("AUTO-1D5D83B4EA", "BND-B85523C283498DD1"),
            ("AUTO-A9B13BB9D4", "BND-E2220EDBEB548F24"),
            ("SROP-RU", "BND-1E41F2571AC3E324"),
            ("AUTO-FE3A699A2D", "AUTO-9E2CFA3779"),
            ("AUTO-067BC58AC6", "BND-E971898775D324AA"),
            ("AUTO-3C76C3AFCE", "BND-5ED8A6B74AC9F746"),
        ]:
            self.assertNotIn(removed, by_id)
            reports = json.loads(by_id[keep]["Bundle_Details_JSON"])
            history = [h for report in reports for h in report.get("catalogIdentityHistory", [])]
            self.assertTrue(any(removed in h["removedProgramIds"] for h in history))
        # Shared institutions/portals do not erase independent tracks or campuses.
        for retained in ("AMGEN-UCSF", "SROP-PU",
                         "AUTO-583E67E91D", "AUTO-6CDAF7E06A", "AUTO-5B0ACCEDAC",
                         "AUTO-ED34824776", "BND-468A7A2484882590"):
            self.assertIn(retained, by_id)

    def test_exclusions_cannot_remove_merge_survivors(self):
        with self.assertRaises(ValueError):
            apply_decisions([], {"merges": [{"keep": "A", "remove": ["B"], "reason": "alias"}],
                                 "exclusions": {"A": "test listing"}})

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

    def test_non_program_pages_cannot_be_imported(self):
        examples = [
            ("Faculty member", "https://example.edu/directory/person/"),
            ("REU search", "https://www.nsf.gov/funding/initiatives/reu/search"),
            ("REU mentors", "https://example.edu/summer-research-program-information-for-mentors/"),
            ("Degree Requirements", "https://example.edu/requirements/"),
            ("REU evaluation", "https://cra.org/cerp/cerp-reu-evaluation/"),
        ]
        for name, url in examples:
            row = dict(Program_ID="TEST", Program_Name=name, Host_Institution="Example",
                       Primary_Field="Multidisciplinary", Cycle_Year="2026",
                       Program_URL=url, Last_Verified="2026-09-16")
            with self.subTest(url=url):
                errors, _ = preflight([row])
                self.assertTrue(any("non-program page" in error for error in errors))
        # Shared network pages and legitimate /programs/ pages remain allowed.
        for url in ("https://example.edu/programs/summer-reu/",
                    "https://btaa.org/resources-for/students/srop/campus-profiles"):
            row.update(Program_Name="Summer Research Program", Program_URL=url)
            self.assertEqual(preflight([row])[0], [])

    def test_automated_retrieval_is_not_verified_eligibility(self):
        rows = load_rows(ROOT / "database/imports/summer_undergraduate_research_opportunities_starter.csv")
        automated = [r for r in rows if r.get("Eligibility_Checked_By", "").startswith("local automated pipeline")]
        self.assertTrue(automated)
        for row in automated:
            self.assertEqual(row["Eligibility_Parse_Status"], "needs_review")
        candidate = dict(automated[0], Eligibility_Parse_Status="reviewed")
        self.assertTrue(any("automated retrieval" in error for error in preflight([candidate])[0]))
        count = self.db.execute("""
            SELECT COUNT(*) FROM source_verifications v JOIN eligibility_rules e USING(cycle_id)
            WHERE e.parse_status='needs_review' AND v.verification_status='verified'
        """).fetchone()[0]
        self.assertEqual(count, 0)

    def test_every_cycle_has_eligibility(self):
        missing = self.db.execute("SELECT COUNT(*) FROM program_cycles c LEFT JOIN eligibility_rules e USING(cycle_id) WHERE e.cycle_id IS NULL").fetchone()[0]
        self.assertEqual(missing, 0)

    def test_historical_cohort_pages_are_not_separate_programs(self):
        urls = {row[0] for row in self.db.execute("SELECT program_url FROM opportunities")}
        self.assertIn("https://cemb.upenn.edu/about-cemb/education-network/undergraduate-research-opportunities/", urls)
        for year in range(2018, 2026):
            self.assertNotIn(f"https://mechanobiology.wustl.edu/{year}-reu-program/", urls)
        self.assertIn("https://www.cnf.cornell.edu/education/reu", urls)
        self.assertNotIn("https://www.cnf.cornell.edu/education/reu/2019", urls)
        self.assertIn("https://www.seasoasa.ucla.edu/surp/", urls)
        self.assertNotIn("https://www.seasoasa.ucla.edu/surp-2/", urls)

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
              AND c.cycle_year = 2026
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
        self.assertEqual(len(rows), self.count("program_cycles"))
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
        self.assertEqual(payload["schema_version"], "1.6.0")

    def test_undated_and_annual_records_share_one_public_program(self):
        from catalog_common import SCHEMA, connect
        from import_catalog import upsert_import
        from export_catalog import export

        row = dict(Program_ID="TEST-UNDATED", Program_Name="Summer Biology Research",
                   Host_Institution="Example University", Primary_Field="Life Sciences",
                   Secondary_Fields="Neuroscience & Cognitive Science",
                   Cycle_Year="", Status="Unknown", Last_Verified="2026-09-18",
                   Program_URL="https://example.edu/summer-research/",
                   Eligibility_Parse_Status="needs_review")
        evidence = dict(url=row["Program_URL"], date_checked="2026-09-18",
                        fields_supported=["Program_Name", "Secondary_Fields"],
                        checked_by="Official source review", limitations="Cycle unknown")
        row["Source_Evidence_JSON"] = json.dumps([evidence])
        self.assertEqual(preflight([row])[0], [])
        self.assertTrue(preflight([row, row])[0])
        for changes in ({"Status": "Open"}, {"Application_Deadline": "2027-01-01"}):
            self.assertTrue(preflight([{**row, **changes}])[0])
        for changes in ({"date_checked": "2026-02-30"},
                        {"fields_supported": ["Stipend_Total_USD"]}):
            invalid = {**row, "Source_Evidence_JSON": json.dumps([{**evidence, **changes}])}
            self.assertTrue(preflight([invalid])[0])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            source = path / "accepted.csv"
            source.write_text("accepted fixture\n")
            database = path / "catalog.sqlite"
            connection = connect(database)
            connection.executescript(SCHEMA.read_text())
            with connection:
                upsert_import(connection, source, [row])
                upsert_import(connection, source, [row])
                upsert_import(connection, source, [{**row, "Cycle_Year": "2027"}])
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM program_cycles").fetchone()[0], 2)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM source_verifications").fetchone()[0], 2)
            connection.close()
            export(database, path / "output")
            catalog = json.loads((path / "output/catalog.json").read_text())
            self.assertEqual(len(catalog["opportunities"]), 1)
            program = catalog["opportunities"][0]
            self.assertEqual([c["cycle_year"] for c in program["cycles"]], [2027, None])
            self.assertIn("Neuroscience & Cognitive Science", [c["category_name"] for c in program["categories"]])
            verifications = json.loads((path / "output/sources.json").read_text())["verifications"]
            self.assertTrue(all(v["fields_supported"] == evidence["fields_supported"] for v in verifications))
            self.assertTrue(all(v["conflict_notes"] == "Cycle unknown" for v in verifications))

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

    def test_identity_names_remove_cycles_but_preserve_meaningful_numbers(self):
        for original, expected in (
            ("2026 UConn REU", "UConn REU"),
            ("AI REU (Summer '26)", "AI REU"),
            ("Math REU26 at Michigan-Dearborn", "Math REU at Michigan-Dearborn"),
            ("Biology REU 2025–2026", "Biology REU"),
            ("Biosphere 2", "Biosphere 2"),
            ("Biozentrum Research Summer", "Biozentrum Research Summer"),
            ("CO2 Chemical Engineering", "CO2 Chemical Engineering"),
            ("3D Interfaces / I3M / E3", "3D Interfaces / I3M / E3"),
        ):
            self.assertEqual(clean_name(original), expected)
            self.assertEqual(clean_name(expected), expected)

    def test_identity_screen_includes_aliases_and_ignores_same_id_cycles(self):
        row = dict(Program_ID="UCONN", Program_Name="UConn Physiology and Neurobiology REU Program",
                   Host_Institution="University of Connecticut", Program_URL="https://pnb.uconn.edu/reu/", Cycle_Year="2025")
        duplicate = dict(row, Program_ID="BUNDLE", Program_Name="REU - UConn Physiology and Neurobiology", Program_URL="https://pnbreu.uconn.edu/", Cycle_Year="")
        self.assertEqual(screen([row, dict(row, Cycle_Year="2026")]), [])
        self.assertEqual(len(screen([row, duplicate])), 1)
        # Identical portals are candidates only: no merge is implicit.
        track = dict(duplicate, Program_ID="OTHER", Program_Name="Separate Partner Track")
        self.assertEqual(len(apply_decisions([duplicate, track], {})), 2)
        self.assertNotEqual(canonical_url("https://example.edu/apply?track=one"), canonical_url("https://example.edu/apply?track=two"))

    def test_identity_merge_preserves_facts_cycles_and_provisional_evidence(self):
        old = dict(Program_ID="STABLE", Program_Name="Example REU", Host_Institution="Example",
                   Cycle_Year="2025", Housing_Included="No", Stipend_Total_USD="5000",
                   Field_Tags="Physics", Last_Verified="2025-01-01", Bundle_Details_JSON="")
        report = {"title": "Example REU 2026", "housingProvision": "provided", "housingCost": "paid", "benefitNotes": "Conditional meal allowance"}
        bundle = dict(old, Program_ID="BUNDLE", Cycle_Year="", Stipend_Total_USD="9000",
                      Housing_Included="Yes", Field_Tags="Biology", Last_Verified="",
                      Catalog_Review_Status="needs_review", Bundle_Details_JSON=json.dumps([report]))
        historical = dict(bundle, Cycle_Year="2024", Stipend_Total_USD="4000", Application_URL="https://example.edu/2024/apply")
        plan = {"merges": [{"keep": "STABLE", "remove": ["BUNDLE"], "reason": "Accepted same-program identity"}]}
        result = apply_decisions([old, bundle, historical], plan)
        self.assertEqual({r["Program_ID"] for r in result}, {"STABLE"})
        self.assertEqual({r["Cycle_Year"] for r in result}, {"2024", "2025"})
        current = next(r for r in result if r["Cycle_Year"] == "2025")
        self.assertEqual(current["Stipend_Total_USD"], "5000")
        self.assertEqual(current["Housing_Included"], "No")
        self.assertEqual(current["Last_Verified"], "2025-01-01")
        self.assertEqual(current["Catalog_Review_Status"], "supplement_needs_review")
        self.assertEqual(current["Field_Tags"], "Physics; Biology")
        stored = json.loads(current["Bundle_Details_JSON"])[0]
        self.assertEqual({key: stored[key] for key in report}, report)
        self.assertEqual(len(stored["catalogIdentityHistory"][0]["originalRows"]), 3)
        self.assertEqual(next(r for r in result if r["Cycle_Year"] == "2024")["Application_URL"], "https://example.edu/2024/apply")
        self.assertEqual(apply_decisions(result, plan), result)
        # An identity merge never makes two provisional sources verified.
        provisional = apply_decisions([dict(bundle, Program_ID="STABLE"), bundle], plan)
        self.assertEqual(provisional[0]["Catalog_Review_Status"], "needs_review")
        self.assertFalse(provisional[0]["Last_Verified"])
        accepted = apply_decisions([
            dict(bundle, Program_ID="STABLE", Catalog_Review_Status="bundle_accepted", Review_Notes=""),
            dict(bundle, Catalog_Review_Status="bundle_accepted", Review_Notes=""),
        ], plan)
        self.assertEqual(accepted[0]["Catalog_Review_Status"], "bundle_accepted")
        self.assertEqual(accepted[0]["Review_Notes"], "")
        self.assertFalse(accepted[0]["Last_Verified"])

    def test_uconn_bundle_alias_has_one_public_identity(self):
        payload = json.loads((ROOT / "data/summer-research/catalog.json").read_text())
        programs = {p["public_id"]: p for p in payload["opportunities"]}
        self.assertIn("UCONN-PNB-REU", programs)
        self.assertNotIn("BND-759781B767455A24", programs)
        self.assertIn("BND-342502C36862A9E3", programs)  # UConn Math is distinct.
        program = programs["UCONN-PNB-REU"]
        self.assertTrue(any(r.get("id") == "program:759781b767455a24" for r in program["bundle_details"]))
        self.assertEqual(program["review_status"], "bundle_accepted")

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
        self.assertIn("international_network", source_types)
        self.assertIn("international_program", source_types)
        text = json.dumps(host_protocol).lower()
        for term in ("neuroscience", "cognitive", "biology", "chemistry", "engineering", "public health", "physics"):
            self.assertIn(term, text)
        scale_targets = host_protocol["scale_targets"]
        self.assertGreaterEqual(scale_targets["design_capacity"]["program_identities"], 5000)
        self.assertGreaterEqual(scale_targets["design_capacity"]["annual_cycle_records_high"], 25000)
        identity_policy = host_protocol["program_identity_policy"]
        self.assertIn("student slots", json.dumps(identity_policy).lower())
        self.assertIn("individual faculty projects", json.dumps(identity_policy).lower())
        source_keys = {row["source_key"] for row in source_catalog}
        for source_key in (
            "mitacs_globalink_research_internship",
            "daad_rise_germany",
            "eth_student_summer_research_fellowship",
            "epfl_life_sciences_summer_research_program",
            "oist_research_internship",
        ):
            self.assertIn(source_key, source_keys)
        pathways = next(row for row in source_catalog if row["source_key"] == "pathways_to_science")
        self.assertTrue(pathways["automated_search_supported"])
        self.assertEqual(pathways["authority_scope"], "discovery_only")
        self.assertIn("programhub", pathways["notes"].lower())

    def test_program_urls_are_preserved_for_public_catalog(self):
        missing = self.db.execute("SELECT COUNT(*) FROM opportunities o LEFT JOIN opportunity_review r USING(opportunity_id) WHERE program_url IS NULL AND COALESCE(r.review_status, '') NOT IN ('needs_review', 'bundle_accepted')").fetchone()[0]
        self.assertEqual(missing, 0)

    def test_provisional_import_does_not_invent_verification_or_eligibility(self):
        rows = load_rows(ROOT / "database/imports/summer_undergraduate_research_opportunities_starter.csv")
        accepted = [r for r in rows if r.get("Catalog_Review_Status") == "bundle_accepted" and not r["Last_Verified"]]
        self.assertTrue(accepted)
        for row in accepted:
            # Accepted programs can retain specific evidence conflicts, including
            # UCSF's new cycle; acceptance must not restore generic warnings.
            if row["Review_Notes"]:
                self.assertIn(row["Program_ID"], {
                    "AMGEN-UCSF", "BND-21B2481861C524C2",
                    "BND-642A3AFAFA140976", "BND-D833CF56CA9DD95D",
                    "BND-4334627EF951B1D4",
                })
            self.assertTrue(json.loads(row["Bundle_Details_JSON"]))
        # Future genuinely provisional imports still cannot invent verification.
        candidate = dict(accepted[0], Catalog_Review_Status="needs_review", Review_Notes="Identity unresolved")
        self.assertTrue(preflight([{**candidate, "Last_Verified": "2026-09-18"}])[0])
        self.assertTrue(preflight([{**candidate, "Eligibility_Parse_Status": "reviewed"}])[0])
        self.assertTrue(preflight([{**candidate, "Review_Notes": ""}])[0])
        # A narrowly verified field may have explicit evidence while the cycle's
        # blanket verification date stays unknown. Require every such event to
        # match accepted source/date/field attribution, never package retrieval.
        accepted_by_cycle = {(r["Program_ID"], int(r["Cycle_Year"]) if r["Cycle_Year"] else None): r for r in accepted}
        cursor = self.db.cursor()
        cursor.row_factory = sqlite3.Row
        events = cursor.execute("SELECT o.public_id, c.cycle_year, v.* FROM opportunity_review r JOIN opportunities o USING(opportunity_id) JOIN program_cycles c USING(opportunity_id) JOIN source_verifications v USING(cycle_id) WHERE r.review_status='bundle_accepted' AND c.last_verified IS NULL").fetchall()
        for event in events:
            row = accepted_by_cycle[(event["public_id"], event["cycle_year"])]
            url = self.db.execute("SELECT source_url FROM sources WHERE source_id=?", (event["source_id"],)).fetchone()[0]
            evidence = next(e for e in json.loads(row["Source_Evidence_JSON"] or "[]") if e["url"] == url and e["date_checked"] == event["date_checked"])
            self.assertEqual(json.loads(event["fields_supported"]), evidence["fields_supported"])
            self.assertEqual(event["checked_by"], evidence["checked_by"])
            self.assertNotIn("Eligibility_Parse_Status", evidence["fields_supported"])
        payload = json.loads((ROOT / "data/summer-research/catalog.json").read_text())
        public = {r["public_id"]: r for r in payload["opportunities"]}
        for row in accepted:
            program = public[row["Program_ID"]]
            self.assertEqual(program["bundle_details"], json.loads(row["Bundle_Details_JSON"]))
            self.assertEqual(program["review_notes"], row["Review_Notes"])
        # A shared ONPRC page describes both an Oregon-only track and a general fellowship.
        self.assertIn("BND-DB88DECA55467223", public)
        for excluded in ("BND-9F88C54D6EEEEC73", "AUTO-66F10F2519", "BND-AA16732F7CF13127"):
            self.assertNotIn(excluded, public)

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
