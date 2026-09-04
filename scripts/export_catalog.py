#!/usr/bin/env python3
"""Create deterministic static JSON exports from SQLite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from catalog_common import DEFAULT_DB, ROOT, connect, dump_json

DEFAULT_OUTPUT = ROOT / "data" / "summer-research"
def records(connection, sql, params=()):
    return [dict(row) for row in connection.execute(sql, params)]


def export(database: Path, output: Path):
    connection = connect(database)
    institutions = records(connection, "SELECT institution_id, institution_slug, institution_name, institution_type, city, state_code, country_code, latitude, longitude, website_url FROM institutions ORDER BY institution_name, city")
    opportunities = records(connection, "SELECT opportunity_id, public_id, institution_id, program_name, network_source, program_type, location_scope, delivery_format, program_url, application_url, notes, active FROM opportunities ORDER BY public_id")
    cycles = records(connection, "SELECT cycle_id, opportunity_id, cycle_year, duration_weeks, program_start, program_end, application_open, application_deadline, application_url, deadline_text, status_code, status_text, stipend_total_usd, stipend_weekly_usd, housing_status, housing_details, meals_status, meals_details, travel_status, travel_details, academic_credit_status, last_verified, data_confidence FROM program_cycles ORDER BY cycle_year DESC, opportunity_id")
    eligibility = records(connection, "SELECT eligibility_rule_id, cycle_id, external_applicants_status, citizenship_rule_text, citizenship_us_citizen, citizenship_permanent_resident, citizenship_international, eligible_years_text, first_year_eligible, sophomore_eligible, junior_eligible, senior_eligible, graduating_senior_eligible, min_gpa, enrolled_required, graduation_rule_text, institution_type_rule_text, two_year_institution_eligible, four_year_institution_eligible, degree_seeking_required, prior_research_status, raw_eligibility_text, other_rule_text, parse_status FROM eligibility_rules ORDER BY cycle_id")
    categories = records(connection, "SELECT category_id, category_slug, category_name, description, sort_order FROM research_categories WHERE active=1 ORDER BY sort_order, category_name")
    tags = records(connection, "SELECT tag_id, tag_slug, tag_name, tag_group, description FROM research_tags WHERE active=1 ORDER BY tag_group, tag_name")
    research_modes = records(connection, "SELECT research_mode_id, mode_code, mode_name, description FROM research_modes WHERE active=1 ORDER BY research_mode_id")
    opportunity_categories = records(connection, "SELECT opportunity_id, category_id, is_primary, assignment_method FROM opportunity_categories ORDER BY opportunity_id, is_primary DESC, category_id")
    opportunity_tags = records(connection, "SELECT opportunity_id, tag_id, source_text, assignment_method FROM opportunity_tags ORDER BY opportunity_id, tag_id")
    opportunity_modes = records(connection, "SELECT opportunity_id, research_mode_id, source_text, assignment_method FROM opportunity_research_modes ORDER BY opportunity_id, research_mode_id")
    sources = records(connection, "SELECT source_id, source_url, source_name, source_type, publisher, authoritative FROM sources ORDER BY source_id")
    verifications = records(connection, "SELECT verification_id, opportunity_id, cycle_id, source_id, date_checked, verification_status, fields_supported, conflict_notes, checked_by, evidence_hash, retrieved_at FROM source_verifications ORDER BY opportunity_id, date_checked DESC")
    for verification in verifications:
        verification["fields_supported"] = json.loads(verification["fields_supported"] or "[]")

    for name, data in {
        "institutions": institutions, "opportunities": opportunities, "program_cycles": cycles,
        "eligibility_rules": eligibility, "research_categories": categories, "research_tags": tags,
        "research_modes": research_modes,
        "sources": {"sources": sources, "verifications": verifications},
    }.items():
        dump_json(output / f"{name}.json", data)

    institution_by_id = {row["institution_id"]: row for row in institutions}
    cycle_by_opportunity = {}
    for cycle in cycles:
        cycle_by_opportunity.setdefault(cycle["opportunity_id"], []).append(cycle)
    eligibility_by_cycle = {row["cycle_id"]: row for row in eligibility}
    category_by_id = {row["category_id"]: row for row in categories}
    tag_by_id = {row["tag_id"]: row for row in tags}
    mode_by_id = {row["research_mode_id"]: row for row in research_modes}
    cats_by_opp, tags_by_opp, modes_by_opp = {}, {}, {}
    for link in opportunity_categories:
        cats_by_opp.setdefault(link["opportunity_id"], []).append({**category_by_id[link["category_id"]], "is_primary": bool(link["is_primary"])})
    for link in opportunity_tags:
        tags_by_opp.setdefault(link["opportunity_id"], []).append(tag_by_id[link["tag_id"]])
    for link in opportunity_modes:
        modes_by_opp.setdefault(link["opportunity_id"], []).append(mode_by_id[link["research_mode_id"]])
    catalog = []
    for opportunity in opportunities:
        item = dict(opportunity)
        item["institution"] = institution_by_id[item.pop("institution_id")]
        item["categories"] = cats_by_opp.get(item["opportunity_id"], [])
        item["tags"] = tags_by_opp.get(item["opportunity_id"], [])
        item["research_modes"] = modes_by_opp.get(item["opportunity_id"], [])
        item["cycles"] = []
        for cycle in cycle_by_opportunity.get(item["opportunity_id"], []):
            cycle_item = dict(cycle)
            cycle_item["eligibility"] = eligibility_by_cycle.get(cycle["cycle_id"])
            item["cycles"].append(cycle_item)
        catalog.append(item)
    schema_version = connection.execute(
        "SELECT value FROM schema_metadata WHERE key='schema_version'"
    ).fetchone()[0]
    dump_json(output / "catalog.json", {"schema_version": schema_version, "opportunities": catalog})

    connection.close()
    return len(catalog)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    count = export(args.database, args.output)
    print(f"Exported {count} opportunities to {args.output}")


if __name__ == "__main__":
    main()
