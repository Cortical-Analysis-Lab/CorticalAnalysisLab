#!/usr/bin/env python3
"""Import or update a reviewed CSV/XLSX catalog into canonical SQLite."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from catalog_common import (
    CATEGORIES, DEFAULT_DB, IMPORTER_VERSION, SCHEMA, TAG_ALIASES, connect,
    int_or_none, iso_date, load_rows, normalize_choice, normalize_country,
    normalize_external, normalize_status, number_or_none, sha256, slugify,
    text_or_none, valid_url,
)

REQUIRED_COLUMNS = {
    "Program_ID", "Program_Name", "Host_Institution", "Primary_Field",
    "Cycle_Year", "Program_URL", "Last_Verified",
}


def preflight(rows):
    errors, warnings = [], []
    if not rows:
        return ["Import contains no records"], warnings
    missing = REQUIRED_COLUMNS - set(rows[0])
    if missing:
        errors.append(f"Missing required columns: {', '.join(sorted(missing))}")
    seen = set()
    for number, row in enumerate(rows, start=2):
        label = row.get("Program_ID") or f"row {number}"
        for field in ("Program_ID", "Program_Name", "Host_Institution", "Cycle_Year"):
            if not text_or_none(row.get(field)):
                errors.append(f"{label}: missing {field}")
        key = (text_or_none(row.get("Program_ID")), int_or_none(row.get("Cycle_Year")))
        if key in seen:
            errors.append(f"{label}: duplicate Program_ID/Cycle_Year {key}")
        seen.add(key)
        for field in ("Program_URL", "Application_URL"):
            value = text_or_none(row.get(field))
            if value and not valid_url(value):
                errors.append(f"{label}: invalid {field}: {value}")
        if not text_or_none(row.get("Primary_Field")):
            warnings.append(f"{label}: missing Primary_Field")
        if not text_or_none(row.get("Last_Verified")):
            warnings.append(f"{label}: missing Last_Verified")
    return errors, warnings


def upsert_import(connection, path, rows):
    cursor = connection.execute(
        "INSERT INTO import_runs(source_filename, source_sha256, row_count, importer_version, status) VALUES (?, ?, ?, ?, 'started')",
        (path.name, sha256(path), len(rows), IMPORTER_VERSION),
    )
    run_id = cursor.lastrowid
    for row_number, row in enumerate(rows, start=2):
        connection.execute(
            "INSERT INTO import_raw_records(import_run_id, row_number, public_id, raw_json) VALUES (?, ?, ?, ?)",
            (run_id, row_number, text_or_none(row.get("Program_ID")), json.dumps(row, ensure_ascii=False, default=str)),
        )
    for order, (slug, name, description) in enumerate(CATEGORIES, start=1):
        connection.execute(
            "INSERT INTO research_categories(category_slug, category_name, description, sort_order) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(category_slug) DO UPDATE SET category_name=excluded.category_name, description=excluded.description, sort_order=excluded.sort_order",
            (slug, name, description, order),
        )

    for row in rows:
        public_id = text_or_none(row["Program_ID"])
        institution_name = text_or_none(row["Host_Institution"])
        city, state = text_or_none(row.get("City")), text_or_none(row.get("State"))
        country = normalize_country(row.get("Country"))
        institution_slug = slugify("-".join(filter(None, [institution_name, city, state, country])))
        connection.execute(
            "INSERT INTO institutions(institution_slug, institution_name, city, state_code, country_code) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(institution_slug) DO UPDATE SET institution_name=excluded.institution_name, city=excluded.city, state_code=excluded.state_code, country_code=excluded.country_code, updated_at=CURRENT_TIMESTAMP",
            (institution_slug, institution_name, city, state, country),
        )
        institution_id = connection.execute("SELECT institution_id FROM institutions WHERE institution_slug=?", (institution_slug,)).fetchone()[0]
        connection.execute(
            "INSERT INTO opportunities(public_id, institution_id, program_name, network_source, program_type, location_scope, delivery_format, program_url, application_url, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(public_id) DO UPDATE SET institution_id=excluded.institution_id, program_name=excluded.program_name, network_source=excluded.network_source, program_type=excluded.program_type, location_scope=excluded.location_scope, delivery_format=excluded.delivery_format, program_url=excluded.program_url, application_url=excluded.application_url, notes=excluded.notes, updated_at=CURRENT_TIMESTAMP",
            (public_id, institution_id, text_or_none(row["Program_Name"]), text_or_none(row.get("Network_Source")), text_or_none(row.get("Program_Type")), text_or_none(row.get("Location_Scope")), text_or_none(row.get("Format")), text_or_none(row.get("Program_URL")), text_or_none(row.get("Application_URL")), text_or_none(row.get("Notes"))),
        )
        opportunity_id = connection.execute("SELECT opportunity_id FROM opportunities WHERE public_id=?", (public_id,)).fetchone()[0]
        cycle_year = int_or_none(row["Cycle_Year"])
        cycle_values = (
            opportunity_id, cycle_year, number_or_none(row.get("Duration_Weeks")), iso_date(row.get("Program_Start")), iso_date(row.get("Program_End")),
            iso_date(row.get("Application_Open")), iso_date(row.get("Application_Deadline")), text_or_none(row.get("Deadline_Text")), normalize_status(row.get("Status")), text_or_none(row.get("Status")),
            number_or_none(row.get("Stipend_Total_USD")), number_or_none(row.get("Stipend_Weekly_USD")), normalize_choice(row.get("Housing_Included")), text_or_none(row.get("Housing_Details")),
            normalize_choice(row.get("Meals_Included")), text_or_none(row.get("Meals_Details")), normalize_choice(row.get("Travel_Included")), text_or_none(row.get("Travel_Details")),
            normalize_choice(row.get("Academic_Credit")), iso_date(row.get("Last_Verified")), text_or_none(row.get("Data_Confidence")),
        )
        connection.execute(
            "INSERT INTO program_cycles(opportunity_id, cycle_year, duration_weeks, program_start, program_end, application_open, application_deadline, deadline_text, status_code, status_text, stipend_total_usd, stipend_weekly_usd, housing_status, housing_details, meals_status, meals_details, travel_status, travel_details, academic_credit_status, last_verified, data_confidence) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(opportunity_id, cycle_year) DO UPDATE SET duration_weeks=excluded.duration_weeks, program_start=excluded.program_start, program_end=excluded.program_end, application_open=excluded.application_open, application_deadline=excluded.application_deadline, deadline_text=excluded.deadline_text, status_code=excluded.status_code, status_text=excluded.status_text, stipend_total_usd=excluded.stipend_total_usd, stipend_weekly_usd=excluded.stipend_weekly_usd, housing_status=excluded.housing_status, housing_details=excluded.housing_details, meals_status=excluded.meals_status, meals_details=excluded.meals_details, travel_status=excluded.travel_status, travel_details=excluded.travel_details, academic_credit_status=excluded.academic_credit_status, last_verified=excluded.last_verified, data_confidence=excluded.data_confidence, updated_at=CURRENT_TIMESTAMP",
            cycle_values,
        )
        cycle_id = connection.execute("SELECT cycle_id FROM program_cycles WHERE opportunity_id=? AND cycle_year=?", (opportunity_id, cycle_year)).fetchone()[0]
        connection.execute(
            "INSERT INTO eligibility_rules(cycle_id, external_applicants_status, citizenship_rule_text, eligible_years_text, min_gpa, parse_status) VALUES (?, ?, ?, ?, ?, 'needs_review') "
            "ON CONFLICT(cycle_id) DO UPDATE SET external_applicants_status=excluded.external_applicants_status, citizenship_rule_text=excluded.citizenship_rule_text, eligible_years_text=excluded.eligible_years_text, min_gpa=excluded.min_gpa, parse_status='needs_review'",
            (cycle_id, normalize_external(row.get("External_Applicants")), text_or_none(row.get("Citizenship")), text_or_none(row.get("Eligible_Years")), number_or_none(row.get("Min_GPA"))),
        )
        connection.execute("DELETE FROM opportunity_categories WHERE opportunity_id=?", (opportunity_id,))
        connection.execute("DELETE FROM opportunity_tags WHERE opportunity_id=?", (opportunity_id,))
        primary = text_or_none(row.get("Primary_Field"))
        category = connection.execute("SELECT category_id FROM research_categories WHERE category_name=?", (primary,)).fetchone()
        if category:
            connection.execute("INSERT OR REPLACE INTO opportunity_categories(opportunity_id, category_id, is_primary, assignment_method) VALUES (?, ?, 1, 'imported')", (opportunity_id, category[0]))
        else:
            category_slug = slugify(primary or "uncategorized")
            connection.execute("INSERT OR IGNORE INTO research_categories(category_slug, category_name, description, sort_order) VALUES (?, ?, 'Imported category requiring review', 999)", (category_slug, primary or "Uncategorized"))
            category_id = connection.execute("SELECT category_id FROM research_categories WHERE category_slug=?", (category_slug,)).fetchone()[0]
            connection.execute("INSERT OR REPLACE INTO opportunity_categories(opportunity_id, category_id, is_primary, assignment_method) VALUES (?, ?, 1, 'imported')", (opportunity_id, category_id))

        raw_tags = [tag.strip() for tag in (text_or_none(row.get("Field_Tags")) or "").split(";") if tag.strip()]
        for raw_tag in raw_tags:
            group, canonical = TAG_ALIASES.get(raw_tag.lower(), ("research_topic", raw_tag))
            tag_slug = slugify(canonical)
            connection.execute("INSERT INTO research_tags(tag_slug, tag_name, tag_group) VALUES (?, ?, ?) ON CONFLICT(tag_slug) DO UPDATE SET tag_name=excluded.tag_name, tag_group=excluded.tag_group", (tag_slug, canonical, group))
            tag_id = connection.execute("SELECT tag_id FROM research_tags WHERE tag_slug=?", (tag_slug,)).fetchone()[0]
            connection.execute("INSERT OR REPLACE INTO opportunity_tags(opportunity_id, tag_id, source_text, assignment_method) VALUES (?, ?, ?, 'imported')", (opportunity_id, tag_id, raw_tag))

        for source_url, source_name, source_type in (
            (text_or_none(row.get("Program_URL")), text_or_none(row.get("Network_Source")) or text_or_none(row.get("Program_Name")), "official_program"),
            (text_or_none(row.get("Application_URL")), f"{text_or_none(row.get('Program_Name'))} application", "official_application"),
        ):
            if not source_url:
                continue
            connection.execute("INSERT INTO sources(source_url, source_name, source_type, authoritative) VALUES (?, ?, ?, 1) ON CONFLICT(source_url) DO UPDATE SET source_name=excluded.source_name", (source_url, source_name, source_type))
            source_id = connection.execute("SELECT source_id FROM sources WHERE source_url=?", (source_url,)).fetchone()[0]
            supported = (
                [key for key, value in row.items() if text_or_none(value) and key not in {"Application_URL"}]
                if source_type == "official_program" else ["Application_URL"]
            )
            connection.execute(
                "INSERT OR IGNORE INTO source_verifications(opportunity_id, cycle_id, source_id, date_checked, verification_status, fields_supported, checked_by) VALUES (?, ?, ?, ?, ?, ?, 'seed_dataset')",
                (opportunity_id, cycle_id, source_id, iso_date(row.get("Last_Verified")), "partially_verified", json.dumps(supported)),
            )
    connection.execute("UPDATE import_runs SET status='completed' WHERE import_run_id=?", (run_id,))
    return run_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    rows = load_rows(args.input)
    errors, warnings = preflight(rows)
    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    if args.dry_run:
        print(f"Preflight passed: {len(rows)} rows, {len(warnings)} warnings")
        return
    args.database.parent.mkdir(parents=True, exist_ok=True)
    connection = connect(args.database)
    try:
        connection.executescript(SCHEMA.read_text(encoding="utf-8"))
        with connection:
            run_id = upsert_import(connection, args.input, rows)
    except sqlite3.Error:
        connection.rollback()
        raise
    finally:
        connection.close()
    print(f"Imported {len(rows)} rows (import run {run_id}) into {args.database}")


if __name__ == "__main__":
    main()
