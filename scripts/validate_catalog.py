#!/usr/bin/env python3
"""Validate relational integrity and flag incomplete or ambiguous catalog data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from catalog_common import DEFAULT_DB, connect, valid_url


def validate(database: Path):
    connection = connect(database)
    errors, warnings = [], []
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        errors.append(f"SQLite integrity check failed: {integrity}")
    foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_keys:
        errors.append(f"Foreign-key violations: {len(foreign_keys)}")
    invalid_supported_fields = connection.execute(
        "SELECT COUNT(*) FROM source_verifications WHERE fields_supported IS NOT NULL AND NOT json_valid(fields_supported)"
    ).fetchone()[0]
    if invalid_supported_fields:
        errors.append(f"Invalid fields_supported JSON values: {invalid_supported_fields}")

    for row in connection.execute("SELECT public_id, program_name, program_url, application_url FROM opportunities ORDER BY public_id"):
        if not row["program_name"]:
            errors.append(f"{row['public_id']}: missing program name")
        for field in ("program_url", "application_url"):
            value = row[field]
            if value and not valid_url(value):
                errors.append(f"{row['public_id']}: invalid {field}: {value}")

    missing_coordinates = connection.execute("SELECT COUNT(*) FROM institutions WHERE latitude IS NULL OR longitude IS NULL").fetchone()[0]
    if missing_coordinates:
        warnings.append(f"{missing_coordinates} institutions need coordinates before map launch")

    query = """
        SELECT o.public_id, c.*, e.eligibility_rule_id, e.parse_status,
               e.citizenship_rule_text, e.eligible_years_text
        FROM program_cycles c
        JOIN opportunities o USING(opportunity_id)
        LEFT JOIN eligibility_rules e USING(cycle_id)
        ORDER BY o.public_id, c.cycle_year
    """
    for row in connection.execute(query):
        label = f"{row['public_id']} ({row['cycle_year']})"
        if not row["eligibility_rule_id"]:
            errors.append(f"{label}: missing eligibility rule")
        if not row["application_deadline"]:
            warnings.append(f"{label}: application deadline unknown")
        if row["duration_weeks"] is None:
            warnings.append(f"{label}: duration unknown")
        if row["stipend_total_usd"] is None and row["stipend_weekly_usd"] is None:
            warnings.append(f"{label}: stipend unknown")
        if row["last_verified"] is None:
            warnings.append(f"{label}: verification date unknown")
        if row["program_start"] and row["program_end"] and row["program_end"] < row["program_start"]:
            errors.append(f"{label}: program_end precedes program_start")
        if row["application_open"] and row["application_deadline"] and row["application_deadline"] < row["application_open"]:
            errors.append(f"{label}: application_deadline precedes application_open")
        if row["application_url"] and not valid_url(row["application_url"]):
            errors.append(f"{label}: invalid cycle application_url: {row['application_url']}")
        if row["parse_status"] == "needs_review":
            warnings.append(f"{label}: eligibility text needs structured review")

    orphan_checks = {
        "opportunities without category": "SELECT COUNT(*) FROM opportunities o LEFT JOIN opportunity_categories oc USING(opportunity_id) WHERE oc.opportunity_id IS NULL",
        "opportunities without source verification": "SELECT COUNT(*) FROM opportunities o LEFT JOIN source_verifications sv USING(opportunity_id) WHERE sv.opportunity_id IS NULL",
    }
    for label, sql in orphan_checks.items():
        count = connection.execute(sql).fetchone()[0]
        if count:
            errors.append(f"{count} {label}")
    counts = {
        table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("institutions", "opportunities", "program_cycles", "eligibility_rules", "research_categories", "research_tags", "research_modes", "opportunity_research_modes", "sources", "source_verifications")
    }
    connection.close()
    return {"valid": not errors, "counts": counts, "errors": errors, "warnings": warnings}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Treat review warnings as failure")
    args = parser.parse_args()
    report = validate(args.database)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("Counts:", ", ".join(f"{key}={value}" for key, value in report["counts"].items()))
        for error in report["errors"]:
            print(f"ERROR: {error}")
        for warning in report["warnings"]:
            print(f"WARNING: {warning}")
        print(f"Validation {'passed' if report['valid'] else 'failed'} with {len(report['warnings'])} review warnings")
    raise SystemExit(0 if report["valid"] and (not args.strict or not report["warnings"]) else 1)


if __name__ == "__main__":
    main()
