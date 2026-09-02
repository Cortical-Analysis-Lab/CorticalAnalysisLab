#!/usr/bin/env python3
"""Small regression suite for the seed architecture."""

import csv
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from catalog_common import (
    DEFAULT_DB, ROOT, disallowed_verification_source, load_rows,
    eligibility_source_matches_official_program,
)
from catalog_staging import (
    add_manual_links, candidate_counts, claim_investigation_batch,
    list_candidates, set_review_status,
)
from run_discovery_session import classify_candidate, deduplicate, nsf_awards, write_progress
from validate_agent_results import validate_results
from automated_investigate_candidates import classify_award, duration_weeks, stipend_amounts
from promote_catalog_candidates import promote, proposal_signature


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
        self.assertEqual(len(rows), self.count("program_cycles"))
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

    def test_agent_batch_claim_marks_candidates_investigating(self):
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory) / "candidates.sqlite"
            ids = add_manual_links([
                "https://example.edu/research/one",
                "https://example.edu/research/two",
            ], "batch test", staging)
            rows = claim_investigation_batch(1, staging)
            self.assertEqual(len(rows), 1)
            statuses = {row["candidate_id"]: row["review_status"] for row in list_candidates(staging)}
            self.assertEqual(statuses[rows[0]["candidate_id"]], "investigating")
            remaining = set(ids) - {rows[0]["candidate_id"]}
            self.assertEqual(statuses[remaining.pop()], "pending")

    def test_discovery_writes_live_progress_files(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            candidate = {
                "candidate_id": "NSF-123", "discovery_source": "source-a",
                "match_state": "NEW_PROGRAM", "matched_public_id": "",
                "match_rationale": "test", "program_name_observed": "Example",
                "institution_observed": "Example University", "cycle_year_observed": "",
                "official_program_url": "", "discovery_source_url": "https://www.nsf.gov/",
                "government_award_id": "123",
                "government_award_url": "https://www.nsf.gov/awardsearch/showAward?AWD_ID=123",
                "verification_status": "discovery_only", "inclusion_status": "not_included",
            }
            write_progress(output, "test-session", datetime.now(timezone.utc).isoformat(), [candidate], [], 35, "source-a")
            progress = json.loads((output / "progress.json").read_text())
            self.assertEqual(progress["discovered_unique"], 1)
            self.assertTrue((output / "candidates.csv").exists())

    def test_agent_results_contract_rejects_missing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_results(Path(directory))
            self.assertTrue(any("Missing required result file" in error for error in errors))

    def test_agent_results_contract_accepts_official_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            results = Path(directory)
            (results / "proposed_records.json").write_text(json.dumps({
                "contract_version": "1.0",
                "generated_at": "2026-09-02T00:00:00+00:00",
                "records": [{
                    "candidate_id": "CAND-1",
                    "proposal_version": "1",
                    "identity": {
                        "program_name": "Example Summer Research",
                        "institution_name": "Example University",
                        "match_state": "NEW_PROGRAM",
                    },
                    "cycle_year": 2027,
                    "classification": {"primary_field": "Life Sciences", "field_tags": [], "research_modes": []},
                    "fields": {"Program_URL": "https://example.edu/research"},
                }],
            }), encoding="utf-8")
            (results / "source_evidence.json").write_text(json.dumps({
                "contract_version": "1.0",
                "generated_at": "2026-09-02T00:00:00+00:00",
                "evidence": [{
                    "candidate_id": "CAND-1",
                    "source_url": "https://example.edu/research",
                    "source_type": "official_program",
                    "authoritative": True,
                    "fields_supported": ["Program_URL"],
                    "evidence_hash": "123456789abc",
                }],
            }), encoding="utf-8")
            (results / "session_report.json").write_text(json.dumps({
                "contract_version": "1.0",
                "generated_at": "2026-09-02T00:00:00+00:00",
                "summary": "Test session",
                "counts": {"discovered": 1, "existing": 0, "ambiguous": 0, "verified": 1, "rejected": 0, "included": 0},
            }), encoding="utf-8")
            self.assertEqual(validate_results(results), [])

    def test_agent_auto_approval_requires_clean_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results = root / "agent_results"
            results.mkdir()
            (results / "proposed_records.json").write_text(json.dumps({
                "contract_version": "1.0",
                "generated_at": "2026-09-02T00:00:00+00:00",
                "records": [
                    {
                        "candidate_id": "CLEAN-1",
                        "proposal_version": "1",
                        "identity": {"program_name": "Clean", "institution_name": "Example", "match_state": "NEW_PROGRAM"},
                        "cycle_year": 2027,
                        "classification": {},
                        "fields": {},
                    },
                    {
                        "candidate_id": "WARN-1",
                        "proposal_version": "1",
                        "identity": {"program_name": "Warn", "institution_name": "Example", "match_state": "NEW_PROGRAM"},
                        "cycle_year": 2027,
                        "classification": {},
                        "fields": {},
                        "validation_warnings": ["needs another look"],
                    },
                ],
            }), encoding="utf-8")
            (results / "source_evidence.json").write_text(json.dumps({
                "contract_version": "1.0",
                "generated_at": "2026-09-02T00:00:00+00:00",
                "evidence": [
                    {
                        "candidate_id": "CLEAN-1",
                        "source_url": "https://example.edu/clean",
                        "source_type": "official_program",
                        "authoritative": True,
                        "fields_supported": ["Program_URL"],
                        "evidence_hash": "clean12345678",
                    },
                    {
                        "candidate_id": "WARN-1",
                        "source_url": "https://example.edu/warn",
                        "source_type": "official_program",
                        "authoritative": True,
                        "fields_supported": ["Program_URL"],
                        "evidence_hash": "warn123456789",
                    },
                ],
            }), encoding="utf-8")
            (results / "session_report.json").write_text(json.dumps({
                "contract_version": "1.0",
                "generated_at": "2026-09-02T00:00:00+00:00",
                "summary": "Test session",
                "counts": {"discovered": 2, "existing": 0, "ambiguous": 0, "verified": 2, "rejected": 0, "included": 0},
            }), encoding="utf-8")
            import importlib.util
            manager_path = ROOT / "local_catalog_manager.py"
            spec = importlib.util.spec_from_file_location("manager_under_test", manager_path)
            manager = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(manager)
            original_results, original_decisions = manager.AGENT_RESULTS_DIR, manager.REVIEW_DECISIONS_PATH
            try:
                manager.AGENT_RESULTS_DIR = results
                manager.REVIEW_DECISIONS_PATH = root / "review_decisions.json"
                result = manager.auto_approve_agent_results()
            finally:
                manager.AGENT_RESULTS_DIR = original_results
                manager.REVIEW_DECISIONS_PATH = original_decisions
            self.assertEqual(result["approved"], ["CLEAN-1"])
            self.assertEqual(result["blocked"][0]["candidate_id"], "WARN-1")

    def test_promotion_updates_existing_missing_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seed = root / "seed.csv"
            seed_rows = load_rows(ROOT / "database" / "imports" / "summer_undergraduate_research_opportunities_starter.csv")
            seed_rows[0]["Program_ID"] = "EXISTING-REU"
            seed_rows[0]["Cycle_Year"] = "2027"
            seed_rows[0]["Duration_Weeks"] = "N/A"
            seed_rows[0]["Application_Deadline"] = "N/A"
            with seed.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(seed_rows[0]))
                writer.writeheader()
                writer.writerows(seed_rows)

            results = root / "agent_results"
            results.mkdir()
            (results / "proposed_records.json").write_text(json.dumps({
                "contract_version": "1.0",
                "generated_at": "2026-09-02T00:00:00+00:00",
                "records": [{
                    "candidate_id": "EXISTING-CANDIDATE",
                    "proposal_version": "1",
                    "identity": {
                        "program_name": "Existing",
                        "institution_name": "Example",
                        "matched_public_id": "EXISTING-REU",
                        "match_state": "EXISTING_PROGRAM",
                    },
                    "cycle_year": 2027,
                    "classification": {},
                    "fields": {
                        "Cycle_Year": 2027,
                        "Duration_Weeks": 10,
                        "Application_Deadline": "2027-02-15",
                    },
                }],
            }), encoding="utf-8")
            (results / "source_evidence.json").write_text(json.dumps({
                "contract_version": "1.0",
                "generated_at": "2026-09-02T00:00:00+00:00",
                "evidence": [{
                    "candidate_id": "EXISTING-CANDIDATE",
                    "source_url": "https://example.edu/existing",
                    "source_type": "official_program",
                    "authoritative": True,
                    "fields_supported": ["Duration_Weeks", "Application_Deadline"],
                    "evidence_hash": "existing123456",
                }],
            }), encoding="utf-8")
            (results / "session_report.json").write_text(json.dumps({
                "contract_version": "1.0",
                "generated_at": "2026-09-02T00:00:00+00:00",
                "summary": "Test session",
                "counts": {"discovered": 1, "existing": 1, "ambiguous": 0, "verified": 1, "rejected": 0, "included": 0},
            }), encoding="utf-8")
            decisions = root / "review_decisions.json"
            decisions.write_text(json.dumps({
                "decisions": {
                    "EXISTING-CANDIDATE": {
                        "decision": "approved",
                        "decided_by": "test",
                        "decided_at": "2026-09-02T00:00:00+00:00",
                        "signature": proposal_signature("EXISTING-CANDIDATE", results),
                    },
                },
            }), encoding="utf-8")

            report = promote(results, decisions, seed, dry_run=True)
            self.assertEqual(report["counts"]["updated"], 1)
            self.assertEqual(report["updates"][0]["program_id"], "EXISTING-REU")
            self.assertEqual(report["canonical_mutation"], "dry_run")

    def test_promotion_blocks_implausible_cycle_years(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seed = root / "seed.csv"
            seed_rows = load_rows(ROOT / "database" / "imports" / "summer_undergraduate_research_opportunities_starter.csv")
            with seed.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(seed_rows[0]))
                writer.writeheader()
                writer.writerows(seed_rows)

            results = root / "agent_results"
            results.mkdir()
            (results / "proposed_records.json").write_text(json.dumps({
                "contract_version": "1.0",
                "generated_at": "2026-09-02T00:00:00+00:00",
                "records": [{
                    "candidate_id": "STALE-2050",
                    "proposal_version": "1",
                    "identity": {"program_name": "Stale", "institution_name": "Example", "match_state": "NEW_PROGRAM"},
                    "cycle_year": 2050,
                    "classification": {},
                    "fields": {"Cycle_Year": 2050, "Program_URL": "https://example.edu/stale"},
                }],
            }), encoding="utf-8")
            (results / "source_evidence.json").write_text(json.dumps({
                "contract_version": "1.0",
                "generated_at": "2026-09-02T00:00:00+00:00",
                "evidence": [{
                    "candidate_id": "STALE-2050",
                    "source_url": "https://example.edu/stale",
                    "source_type": "official_program",
                    "authoritative": True,
                    "fields_supported": ["Cycle_Year"],
                    "evidence_hash": "stale2050123",
                }],
            }), encoding="utf-8")
            (results / "session_report.json").write_text(json.dumps({
                "contract_version": "1.0",
                "generated_at": "2026-09-02T00:00:00+00:00",
                "summary": "Test session",
                "counts": {"discovered": 1, "existing": 0, "ambiguous": 0, "verified": 1, "rejected": 0, "included": 0},
            }), encoding="utf-8")
            decisions = root / "review_decisions.json"
            decisions.write_text(json.dumps({
                "decisions": {
                    "STALE-2050": {
                        "decision": "approved",
                        "decided_by": "test",
                        "decided_at": "2026-09-02T00:00:00+00:00",
                        "signature": proposal_signature("STALE-2050", results),
                    },
                },
            }), encoding="utf-8")

            report = promote(results, decisions, seed, dry_run=True)
            self.assertTrue(any("implausible cycle year" in item["reason"] for item in report["rejected"]))
            self.assertEqual(report["blocked"], [])

    def test_automated_investigation_triages_nsf_awards(self):
        candidate = {"observed_name": "", "observed_institution": ""}
        action, _ = classify_award(candidate, {
            "title": "REU Site: Summer Research Program in Ecology",
            "program": "REU SITE-Res Exp for Ugrd Site",
            "fundProgramName": "RSCH EXPER FOR UNDERGRAD SITES",
            "abstractText": "This REU Site award supports students for 10 weeks.",
        })
        self.assertEqual(action, "propose")
        action, _ = classify_award(candidate, {
            "title": "CAREER: Hydrological Sensitivity Across Timescales",
            "program": "CAREER",
            "fundProgramName": "",
            "abstractText": "Research award for a faculty investigator.",
        })
        self.assertEqual(action, "reject")
        action, _ = classify_award(candidate, {
            "title": "Materials Research Science and Engineering Center",
            "program": "MRSEC",
            "fundProgramName": "",
            "abstractText": "The center supports Research Experiences for Undergraduates among broader activities.",
        })
        self.assertEqual(action, "reject")

    def test_automated_investigation_parses_optional_field_variants(self):
        self.assertEqual(duration_weeks("Students complete a 10-week research program."), 10)
        self.assertEqual(duration_weeks("Participants spend ten weeks in the lab."), 10)
        self.assertEqual(duration_weeks("The institute includes a 12 wk summer experience."), 12)

        self.assertEqual(stipend_amounts("Participants receive a $6,000 stipend."), (6000.0, None))
        self.assertEqual(stipend_amounts("Students receive a stipend of $600 per week."), (None, 600.0))
        self.assertEqual(stipend_amounts("The total award is $359,991 over three years."), (None, None))

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
