#!/usr/bin/env python3
"""Promote approved local catalog candidates after structured review.

This first promotion guard validates the handoff contract and reviewer approvals,
then emits audit reports. It intentionally refuses to mutate canonical data until
records can be mapped into reviewed import artifacts without ambiguity.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from catalog_common import ROOT, load_rows
from import_catalog import preflight
from validate_agent_results import DEFAULT_RESULTS_DIR, validate_results


DEFAULT_DECISIONS = ROOT / "database" / "local" / "review_decisions.json"
DEFAULT_REPORT_DIR = ROOT / "database" / "local" / "promotion_reports"
DEFAULT_SEED = ROOT / "database" / "imports" / "summer_undergraduate_research_opportunities_starter.csv"
AMBIGUOUS_STATES = {"POSSIBLE_DUPLICATE", "AMBIGUOUS"}
VISIBLE_NA_FIELDS = {
    "Duration_Weeks",
    "Program_Start",
    "Program_End",
    "Application_Open",
    "Application_Deadline",
    "Deadline_Text",
    "Stipend_Total_USD",
    "Stipend_Weekly_USD",
}
UPDATABLE_FIELDS = VISIBLE_NA_FIELDS | {
    "Application_URL",
    "Status",
    "Last_Verified",
    "Data_Confidence",
    "Raw_Eligibility_Text",
    "Eligibility_Source_URL",
    "Eligibility_Checked_On",
    "Eligibility_Checked_By",
}


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def proposal_signature(candidate_id, results_dir):
    digest = hashlib.sha256(candidate_id.encode())
    for filename in ("proposed_records.json", "source_evidence.json"):
        path = Path(results_dir) / filename
        if path.exists():
            digest.update(file_sha256(path).encode())
    return digest.hexdigest()


def normalize_program_id(program_id):
    if re.match(r"^NSF-\d+$", program_id or ""):
        return program_id.replace("NSF-", "NSF-REU-", 1)
    return program_id


def normalize_seed_row(row):
    row = dict(row)
    row["Program_ID"] = normalize_program_id(row.get("Program_ID"))
    for field in VISIBLE_NA_FIELDS:
        if field in row and not (row.get(field) or "").strip():
            row[field] = "N/A"
    if row["Program_ID"].startswith("NSF-REU-"):
        row["Eligibility_Parse_Status"] = "reviewed"
        row["Eligibility_Source_URL"] = row.get("Eligibility_Source_URL") or row.get("Program_URL")
        row["Eligibility_Checked_On"] = row.get("Eligibility_Checked_On") or row.get("Last_Verified") or datetime.now(timezone.utc).date().isoformat()
        row["Eligibility_Checked_By"] = row.get("Eligibility_Checked_By") or "automated_nsf_metadata"
    return row


def is_missing(value):
    return not (str(value or "").strip()) or str(value).strip().lower() in {"n/a", "na", "not applicable"}


def real_value(value):
    return value is not None and str(value).strip() and not is_missing(value)


def plausible_cycle_year(value):
    try:
        year = int(value)
    except (TypeError, ValueError):
        return False
    current_year = datetime.now(timezone.utc).year
    return current_year - 1 <= year <= current_year + 5


def normalized_seed_rows(seed_path):
    rows = []
    seen = set()
    for row in load_rows(seed_path):
        normalized = normalize_seed_row(row)
        key = (normalized.get("Program_ID"), normalized.get("Cycle_Year"))
        if key in seen:
            continue
        seen.add(key)
        rows.append(normalized)
    return rows


def promotion_report(results_dir, decisions_path):
    errors = validate_results(results_dir)
    proposed = read_json(Path(results_dir) / "proposed_records.json", {"records": []})
    evidence = read_json(Path(results_dir) / "source_evidence.json", {"evidence": []})
    decisions = read_json(decisions_path, {"decisions": {}}).get("decisions", {})
    evidence_by_candidate = {}
    for item in evidence.get("evidence", []):
        evidence_by_candidate.setdefault(item.get("candidate_id"), []).append(item)

    approved, rejected, blocked = [], [], []
    for record in proposed.get("records", []):
        candidate_id = record.get("candidate_id")
        identity = record.get("identity", {})
        decision = decisions.get(candidate_id)
        if not decision or decision.get("decision") != "approved":
            rejected.append({"candidate_id": candidate_id, "reason": "not approved"})
            continue
        if decision.get("signature") != proposal_signature(candidate_id, results_dir):
            blocked.append({"candidate_id": candidate_id, "reason": "approval is stale"})
            continue
        if identity.get("match_state") in AMBIGUOUS_STATES:
            blocked.append({"candidate_id": candidate_id, "reason": "ambiguous duplicate classification"})
            continue
        if record.get("conflicts"):
            blocked.append({"candidate_id": candidate_id, "reason": "proposal contains conflicts"})
            continue
        official = [
            item for item in evidence_by_candidate.get(candidate_id, [])
            if item.get("authoritative") and item.get("source_type") != "discovery_only"
        ]
        if not official:
            blocked.append({"candidate_id": candidate_id, "reason": "missing authoritative official evidence"})
            continue
        approved.append({
            "candidate_id": candidate_id,
            "match_state": identity.get("match_state"),
            "decided_by": decision.get("decided_by", "unknown"),
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results_dir": str(results_dir),
        "validation_errors": errors,
        "approved": approved,
        "rejected": rejected,
        "blocked": blocked,
        "counts": {
            "approved": len(approved),
            "rejected": len(rejected),
            "blocked": len(blocked),
        },
        "canonical_mutation": "not_performed",
        "next_step": "Append approved proposals to reviewed import CSV, then run deterministic rebuild.",
    }


def appendable_rows(results_dir, decisions_path, seed_path):
    report = promotion_report(results_dir, decisions_path)
    if report["validation_errors"] or report["blocked"]:
        return report, [], normalized_seed_rows(seed_path)
    approved_ids = {item["candidate_id"] for item in report["approved"]}
    proposed = read_json(Path(results_dir) / "proposed_records.json", {"records": []}).get("records", [])
    seed_rows = normalized_seed_rows(seed_path)
    headers = list(seed_rows[0])
    rows_by_id_cycle = {(row.get("Program_ID"), str(row.get("Cycle_Year"))): row for row in seed_rows}
    existing_ids = {row.get("Program_ID") for row in seed_rows}
    rows = []
    updates = []
    for record in proposed:
        candidate_id = record.get("candidate_id")
        if candidate_id not in approved_ids:
            continue
        identity = record.get("identity", {})
        fields = record.get("fields", {})
        program_id = normalize_program_id(
            identity.get("matched_public_id") or identity.get("public_id") or candidate_id
        )
        cycle_year = str(fields.get("Cycle_Year") or record.get("cycle_year") or "")
        if not plausible_cycle_year(cycle_year):
            report["rejected"].append({"candidate_id": candidate_id, "reason": f"implausible cycle year: {cycle_year}"})
            continue
        existing_row = rows_by_id_cycle.get((program_id, cycle_year))
        if existing_row:
            changed = []
            for field in UPDATABLE_FIELDS:
                if field not in existing_row or field not in fields:
                    continue
                value = fields.get(field)
                if real_value(value) and is_missing(existing_row.get(field)):
                    existing_row[field] = str(value)
                    changed.append(field)
            if changed:
                updates.append({"candidate_id": candidate_id, "program_id": program_id, "cycle_year": cycle_year, "fields": changed})
            else:
                report["rejected"].append({"candidate_id": candidate_id, "reason": f"Program_ID/Cycle_Year already current or has no new non-N/A fields: {program_id} {cycle_year}"})
            continue
        row = {header: "" for header in headers}
        row.update({key: "" if value is None else value for key, value in fields.items() if key in row})
        row["Program_ID"] = program_id
        row["Program_Name"] = fields.get("Program_Name") or identity.get("program_name")
        row["Host_Institution"] = fields.get("Host_Institution") or identity.get("institution_name")
        row["Primary_Field"] = record.get("classification", {}).get("primary_field") or fields.get("Primary_Field") or "Multidisciplinary"
        row["Field_Tags"] = "; ".join(record.get("classification", {}).get("field_tags", []))
        row["Cycle_Year"] = fields.get("Cycle_Year") or record.get("cycle_year")
        row["Program_URL"] = fields.get("Program_URL")
        row["Application_URL"] = fields.get("Application_URL") or fields.get("Program_URL")
        row["Last_Verified"] = fields.get("Last_Verified") or datetime.now(timezone.utc).date().isoformat()
        row["Data_Confidence"] = fields.get("Data_Confidence") or "medium"
        row["Eligibility_Parse_Status"] = fields.get("Eligibility_Parse_Status") or "reviewed"
        row["Eligibility_Source_URL"] = fields.get("Eligibility_Source_URL") or row["Program_URL"]
        row["Eligibility_Checked_On"] = fields.get("Eligibility_Checked_On") or row["Last_Verified"]
        row["Eligibility_Checked_By"] = fields.get("Eligibility_Checked_By") or "automated_agent"
        for field in VISIBLE_NA_FIELDS:
            row[field] = row.get(field) or "N/A"
        rows.append(row)
        existing_ids.add(program_id)
    report["updates"] = updates
    report["counts"]["updated"] = len(updates)
    report["counts"]["rejected"] = len(report["rejected"])
    report["counts"]["blocked"] = len(report["blocked"])
    return report, rows, seed_rows


def promote(results_dir, decisions_path, seed_path, dry_run=False):
    report, new_rows, current_rows = appendable_rows(results_dir, decisions_path, seed_path)
    if report["validation_errors"] or report["blocked"]:
        return report
    if not new_rows and not report.get("updates"):
        report["canonical_mutation"] = "no_new_rows"
        return report
    headers = list(current_rows[0])
    merged_rows = current_rows + new_rows
    errors, warnings = preflight(merged_rows)
    report["preflight_warnings"] = warnings
    if errors:
        report["blocked"].extend({"candidate_id": "preflight", "reason": error} for error in errors)
        return report
    if dry_run:
        report["canonical_mutation"] = "dry_run"
        report["new_rows"] = len(new_rows)
        report["updated_rows"] = len(report.get("updates", []))
        return report
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        candidate_csv = temporary / seed_path.name
        with candidate_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            writer.writerows(merged_rows)
        test_db = temporary / "catalog.sqlite"
        subprocess.run([sys.executable, ROOT / "scripts" / "import_catalog.py", candidate_csv, "--database", test_db],
                       cwd=ROOT, check=True, capture_output=True, text=True)
        subprocess.run([sys.executable, ROOT / "scripts" / "validate_catalog.py", "--database", test_db],
                       cwd=ROOT, check=True, capture_output=True, text=True)
        shutil.copyfile(candidate_csv, seed_path)
    report["canonical_mutation"] = "reviewed_import_csv_updated"
    report["new_rows"] = len(new_rows)
    report["updated_rows"] = len(report.get("updates", []))
    report["next_step"] = "Run python scripts/rebuild_database.py, python scripts/test_catalog.py, and python scripts/export_review_xlsx.py."
    return report


def write_reports(report, report_dir):
    report_dir.mkdir(parents=True, exist_ok=True)
    stem = datetime.now(timezone.utc).strftime("promotion-%Y%m%dT%H%M%SZ")
    json_path = report_dir / f"{stem}.json"
    md_path = report_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Catalog promotion report",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Approved candidates: {report['counts']['approved']}",
        f"- Rejected/unapproved candidates: {report['counts']['rejected']}",
        f"- Blocked candidates: {report['counts']['blocked']}",
        f"- Existing catalog rows updated: {report['counts'].get('updated', 0)}",
        f"- Canonical mutation: {report['canonical_mutation']}",
        "",
        "## Blocked",
        "",
    ]
    lines.extend([f"- {item['candidate_id']}: {item['reason']}" for item in report["blocked"]] or ["- None"])
    lines.extend(["", "## Approved", ""])
    lines.extend([f"- {item['candidate_id']} ({item['decided_by']})" for item in report["approved"]] or ["- None"])
    lines.extend(["", "## Updated existing rows", ""])
    lines.extend([
        f"- {item['program_id']} ({item['cycle_year']}): {', '.join(item['fields'])}"
        for item in report.get("updates", [])
    ] or ["- None"])
    lines.extend(["", "## Next step", "", report["next_step"]])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--approved-only", action="store_true", required=True)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        report = promote(args.results_dir, args.decisions, args.seed, args.dry_run)
    except (subprocess.CalledProcessError, sqlite3.Error) as error:
        report = promotion_report(args.results_dir, args.decisions)
        report["blocked"].append({"candidate_id": "promotion", "reason": f"{type(error).__name__}: {error}"})
    json_path, md_path = write_reports(report, args.report_dir)
    print(f"Promotion report: {json_path}")
    print(f"Promotion summary: {md_path}")
    if report["validation_errors"] or report["blocked"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
