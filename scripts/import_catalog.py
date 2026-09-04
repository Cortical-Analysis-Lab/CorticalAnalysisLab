#!/usr/bin/env python3
"""Import or update accepted CSV catalog data in SQLite."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from catalog_common import (
    CATEGORIES, DEFAULT_DB, IMPORTER_VERSION, MODE_ALIASES, RESEARCH_MODES,
    SCHEMA, TAG_ALIASES, connect,
    int_or_none, iso_date, load_rows, normalize_choice, normalize_country,
    normalize_external, normalize_status, number_or_none, research_modes_from_tag,
    sha256, slugify,
    text_or_none, valid_url,
)

REQUIRED_COLUMNS = {
    "Program_ID", "Program_Name", "Host_Institution", "Primary_Field",
    "Cycle_Year", "Program_URL", "Last_Verified",
}
DISCOVERY_SOURCE_SEED = DEFAULT_DB.parents[1] / "database" / "discovery" / "source_catalog_seed.json"

ELIGIBILITY_BOOLEAN_COLUMNS = {
    "Citizenship_US_Citizen", "Citizenship_Permanent_Resident", "Citizenship_International",
    "First_Year_Eligible", "Sophomore_Eligible", "Junior_Eligible", "Senior_Eligible",
    "Graduating_Senior_Eligible", "Enrolled_Required", "Two_Year_Institution_Eligible",
    "Four_Year_Institution_Eligible", "Degree_Seeking_Required",
}


def reviewed_bool(value):
    """Parse only explicit staging booleans; blanks remain unknown."""
    value = (text_or_none(value) or "").lower()
    if value in {"1", "yes", "true"}:
        return 1
    if value in {"0", "no", "false"}:
        return 0
    return None


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
        eligibility_url = text_or_none(row.get("Eligibility_Source_URL"))
        if eligibility_url and not valid_url(eligibility_url):
            errors.append(f"{label}: invalid Eligibility_Source_URL: {eligibility_url}")
        if not text_or_none(row.get("Primary_Field")):
            warnings.append(f"{label}: missing Primary_Field")
        if not text_or_none(row.get("Last_Verified")):
            warnings.append(f"{label}: missing Last_Verified")
        for field in ELIGIBILITY_BOOLEAN_COLUMNS:
            value = text_or_none(row.get(field))
            if value and value.lower() not in {"0", "1", "yes", "no", "true", "false"}:
                errors.append(f"{label}: invalid {field}: {value}")
        parse_status = text_or_none(row.get("Eligibility_Parse_Status"))
        if parse_status and parse_status not in {"reviewed", "needs_review", "not_applicable"}:
            errors.append(f"{label}: invalid Eligibility_Parse_Status: {parse_status}")
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
    for mode_code, mode_name, description in RESEARCH_MODES:
        connection.execute(
            "INSERT INTO research_modes(mode_code, mode_name, description) VALUES (?, ?, ?) "
            "ON CONFLICT(mode_code) DO UPDATE SET mode_name=excluded.mode_name, description=excluded.description",
            (mode_code, mode_name, description),
        )
    seed_discovery_sources(connection)

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
            iso_date(row.get("Application_Open")), iso_date(row.get("Application_Deadline")), text_or_none(row.get("Application_URL")), text_or_none(row.get("Deadline_Text")), normalize_status(row.get("Status")), text_or_none(row.get("Status")),
            number_or_none(row.get("Stipend_Total_USD")), number_or_none(row.get("Stipend_Weekly_USD")), normalize_choice(row.get("Housing_Included")), text_or_none(row.get("Housing_Details")),
            normalize_choice(row.get("Meals_Included")), text_or_none(row.get("Meals_Details")), normalize_choice(row.get("Travel_Included")), text_or_none(row.get("Travel_Details")),
            normalize_choice(row.get("Academic_Credit")), iso_date(row.get("Last_Verified")), text_or_none(row.get("Data_Confidence")),
        )
        connection.execute(
            "INSERT INTO program_cycles(opportunity_id, cycle_year, duration_weeks, program_start, program_end, application_open, application_deadline, application_url, deadline_text, status_code, status_text, stipend_total_usd, stipend_weekly_usd, housing_status, housing_details, meals_status, meals_details, travel_status, travel_details, academic_credit_status, last_verified, data_confidence) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(opportunity_id, cycle_year) DO UPDATE SET duration_weeks=excluded.duration_weeks, program_start=excluded.program_start, program_end=excluded.program_end, application_open=excluded.application_open, application_deadline=excluded.application_deadline, application_url=excluded.application_url, deadline_text=excluded.deadline_text, status_code=excluded.status_code, status_text=excluded.status_text, stipend_total_usd=excluded.stipend_total_usd, stipend_weekly_usd=excluded.stipend_weekly_usd, housing_status=excluded.housing_status, housing_details=excluded.housing_details, meals_status=excluded.meals_status, meals_details=excluded.meals_details, travel_status=excluded.travel_status, travel_details=excluded.travel_details, academic_credit_status=excluded.academic_credit_status, last_verified=excluded.last_verified, data_confidence=excluded.data_confidence, updated_at=CURRENT_TIMESTAMP",
            cycle_values,
        )
        cycle_id = connection.execute("SELECT cycle_id FROM program_cycles WHERE opportunity_id=? AND cycle_year=?", (opportunity_id, cycle_year)).fetchone()[0]
        prior_research = normalize_choice(row.get("Prior_Research_Status"))
        if prior_research not in {"required", "preferred", "not_required", "unknown"}:
            prior_research = "unknown"
        parse_status = text_or_none(row.get("Eligibility_Parse_Status")) or "needs_review"
        raw_eligibility = text_or_none(row.get("Raw_Eligibility_Text")) or " | ".join(filter(None, [text_or_none(row.get("External_Applicants")), text_or_none(row.get("Citizenship")), text_or_none(row.get("Eligible_Years"))])) or None
        eligibility_values = (
            cycle_id, normalize_external(row.get("External_Applicants")), text_or_none(row.get("Citizenship")),
            reviewed_bool(row.get("Citizenship_US_Citizen")), reviewed_bool(row.get("Citizenship_Permanent_Resident")), reviewed_bool(row.get("Citizenship_International")),
            text_or_none(row.get("Eligible_Years")), reviewed_bool(row.get("First_Year_Eligible")), reviewed_bool(row.get("Sophomore_Eligible")),
            reviewed_bool(row.get("Junior_Eligible")), reviewed_bool(row.get("Senior_Eligible")), reviewed_bool(row.get("Graduating_Senior_Eligible")),
            number_or_none(row.get("Min_GPA")), reviewed_bool(row.get("Enrolled_Required")), text_or_none(row.get("Graduation_Rule_Text")),
            text_or_none(row.get("Institution_Type_Rule_Text")), reviewed_bool(row.get("Two_Year_Institution_Eligible")), reviewed_bool(row.get("Four_Year_Institution_Eligible")),
            reviewed_bool(row.get("Degree_Seeking_Required")), prior_research, raw_eligibility, text_or_none(row.get("Other_Rule_Text")), parse_status,
        )
        connection.execute(
            "INSERT INTO eligibility_rules(cycle_id, external_applicants_status, citizenship_rule_text, citizenship_us_citizen, citizenship_permanent_resident, citizenship_international, eligible_years_text, first_year_eligible, sophomore_eligible, junior_eligible, senior_eligible, graduating_senior_eligible, min_gpa, enrolled_required, graduation_rule_text, institution_type_rule_text, two_year_institution_eligible, four_year_institution_eligible, degree_seeking_required, prior_research_status, raw_eligibility_text, other_rule_text, parse_status) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(cycle_id) DO UPDATE SET external_applicants_status=excluded.external_applicants_status, citizenship_rule_text=excluded.citizenship_rule_text, citizenship_us_citizen=excluded.citizenship_us_citizen, citizenship_permanent_resident=excluded.citizenship_permanent_resident, citizenship_international=excluded.citizenship_international, eligible_years_text=excluded.eligible_years_text, first_year_eligible=excluded.first_year_eligible, sophomore_eligible=excluded.sophomore_eligible, junior_eligible=excluded.junior_eligible, senior_eligible=excluded.senior_eligible, graduating_senior_eligible=excluded.graduating_senior_eligible, min_gpa=excluded.min_gpa, enrolled_required=excluded.enrolled_required, graduation_rule_text=excluded.graduation_rule_text, institution_type_rule_text=excluded.institution_type_rule_text, two_year_institution_eligible=excluded.two_year_institution_eligible, four_year_institution_eligible=excluded.four_year_institution_eligible, degree_seeking_required=excluded.degree_seeking_required, prior_research_status=excluded.prior_research_status, raw_eligibility_text=excluded.raw_eligibility_text, other_rule_text=excluded.other_rule_text, parse_status=excluded.parse_status",
            eligibility_values,
        )
        connection.execute("DELETE FROM opportunity_categories WHERE opportunity_id=?", (opportunity_id,))
        connection.execute("DELETE FROM opportunity_tags WHERE opportunity_id=?", (opportunity_id,))
        connection.execute("DELETE FROM opportunity_research_modes WHERE opportunity_id=?", (opportunity_id,))
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
            mode_codes = set(research_modes_from_tag(raw_tag))
            alias_mode = MODE_ALIASES.get(raw_tag.lower())
            if alias_mode:
                mode_codes.add(alias_mode)
            for mode_code in sorted(mode_codes):
                research_mode_id = connection.execute("SELECT research_mode_id FROM research_modes WHERE mode_code=?", (mode_code,)).fetchone()[0]
                connection.execute("INSERT OR REPLACE INTO opportunity_research_modes(opportunity_id, research_mode_id, source_text, assignment_method) VALUES (?, ?, ?, 'explicit_seed_tag')", (opportunity_id, research_mode_id, raw_tag))

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
        eligibility_source_url = text_or_none(row.get("Eligibility_Source_URL"))
        if eligibility_source_url:
            connection.execute("INSERT INTO sources(source_url, source_name, source_type, authoritative) VALUES (?, ?, 'official_program', 1) ON CONFLICT(source_url) DO NOTHING", (eligibility_source_url, f"{text_or_none(row.get('Program_Name'))} eligibility"))
            source_id = connection.execute("SELECT source_id FROM sources WHERE source_url=?", (eligibility_source_url,)).fetchone()[0]
            eligibility_fields = ["eligibility_rules." + field for field in (
                "external_applicants_status", "citizenship_rule_text", "citizenship_us_citizen", "citizenship_permanent_resident", "citizenship_international",
                "eligible_years_text", "first_year_eligible", "sophomore_eligible", "junior_eligible", "senior_eligible", "graduating_senior_eligible",
                "min_gpa", "enrolled_required", "graduation_rule_text", "institution_type_rule_text", "two_year_institution_eligible",
                "four_year_institution_eligible", "degree_seeking_required", "prior_research_status", "raw_eligibility_text", "other_rule_text", "parse_status",
            )]
            existing = connection.execute("SELECT fields_supported FROM source_verifications WHERE opportunity_id=? AND cycle_id=? AND source_id=? AND date_checked=?", (opportunity_id, cycle_id, source_id, iso_date(row.get("Eligibility_Checked_On")) or iso_date(row.get("Last_Verified")))).fetchone()
            supported = sorted(set((json.loads(existing[0]) if existing and existing[0] else []) + eligibility_fields))
            connection.execute(
                "INSERT INTO source_verifications(opportunity_id, cycle_id, source_id, date_checked, verification_status, fields_supported, checked_by) VALUES (?, ?, ?, ?, 'verified', ?, ?) "
                "ON CONFLICT(opportunity_id, cycle_id, source_id, date_checked) DO UPDATE SET verification_status='verified', fields_supported=excluded.fields_supported, checked_by=excluded.checked_by, retrieved_at=NULL",
                (opportunity_id, cycle_id, source_id, iso_date(row.get("Eligibility_Checked_On")) or iso_date(row.get("Last_Verified")), json.dumps(supported), text_or_none(row.get("Eligibility_Checked_By")) or "reviewed_import"),
            )
    connection.execute("UPDATE import_runs SET status='completed' WHERE import_run_id=?", (run_id,))
    return run_id


def seed_discovery_sources(connection):
    if not DISCOVERY_SOURCE_SEED.exists():
        return
    records = json.loads(DISCOVERY_SOURCE_SEED.read_text(encoding="utf-8"))
    for item in records:
        connection.execute(
            """
            INSERT INTO discovery_sources(
                source_key, source_name, source_type, source_url, source_priority,
                discovery_pass, automated_search_supported, authority_scope, notes, active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(source_key) DO UPDATE SET
                source_name=excluded.source_name,
                source_type=excluded.source_type,
                source_url=excluded.source_url,
                source_priority=excluded.source_priority,
                discovery_pass=excluded.discovery_pass,
                automated_search_supported=excluded.automated_search_supported,
                authority_scope=excluded.authority_scope,
                notes=excluded.notes,
                active=excluded.active,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                item["source_key"],
                item["source_name"],
                item["source_type"],
                item.get("source_url"),
                int(item.get("source_priority", 999)),
                int(item["discovery_pass"]),
                1 if item.get("automated_search_supported") else 0,
                item.get("authority_scope", "discovery_only"),
                item.get("notes"),
            ),
        )


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
