#!/usr/bin/env python3
"""Apply accepted duplicate identity recommendations to the reviewed import CSV."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from catalog_common import ROOT, load_rows, text_or_none
from review_duplicate_identities import (
    DEFAULT_IMPORT,
    DEFAULT_OUTPUT as DEFAULT_REVIEW,
    build_review_rows,
)


DEFAULT_LOG = ROOT / "database" / "local" / "review" / "duplicate_identity_apply_log.csv"
DEFAULT_SUMMARY = ROOT / "database" / "local" / "review" / "duplicate_identity_apply_log.md"
MERGE_FILL_FIELDS = (
    "Network_Source",
    "Program_Type",
    "Primary_Field",
    "Field_Tags",
    "City",
    "State",
    "Country",
    "Location_Scope",
    "Format",
    "External_Applicants",
    "Citizenship",
    "Eligible_Years",
    "Min_GPA",
    "Duration_Weeks",
    "Program_Start",
    "Program_End",
    "Application_Open",
    "Application_Deadline",
    "Deadline_Text",
    "Status",
    "Stipend_Total_USD",
    "Stipend_Weekly_USD",
    "Housing_Included",
    "Housing_Details",
    "Meals_Included",
    "Meals_Details",
    "Travel_Included",
    "Travel_Details",
    "Academic_Credit",
    "Application_URL",
    "Data_Confidence",
    "Eligibility_Parse_Status",
    "Citizenship_US_Citizen",
    "Citizenship_Permanent_Resident",
    "Citizenship_International",
    "First_Year_Eligible",
    "Sophomore_Eligible",
    "Junior_Eligible",
    "Senior_Eligible",
    "Graduating_Senior_Eligible",
    "Enrolled_Required",
    "Graduation_Rule_Text",
    "Institution_Type_Rule_Text",
    "Two_Year_Institution_Eligible",
    "Four_Year_Institution_Eligible",
    "Degree_Seeking_Required",
    "Prior_Research_Status",
    "Raw_Eligibility_Text",
    "Other_Rule_Text",
    "Eligibility_Source_URL",
    "Eligibility_Checked_On",
    "Eligibility_Checked_By",
)


def normalized(value):
    return (text_or_none(value) or "").strip()


def blank(value):
    value = normalized(value)
    return not value or value.upper() == "N/A"


def combine_text(*values):
    parts = []
    seen = set()
    for value in values:
        for part in (normalized(value) or "").split(";"):
            clean = part.strip()
            if clean and clean.upper() != "N/A" and clean.lower() not in seen:
                parts.append(clean)
                seen.add(clean.lower())
    return "; ".join(parts)


def confidence_rank(value):
    return {
        "low": 1,
        "medium": 2,
        "medium-high": 3,
        "high": 4,
    }.get(normalized(value).lower(), 0)


def better_confidence(current, candidate):
    return confidence_rank(candidate) > confidence_rank(current)


def read_review_rows(path, import_path):
    if path.exists():
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
    return build_review_rows(load_rows(import_path))


def merge_into_keep(keep, removed_rows, review_rows):
    changed_fields = []
    for removed in removed_rows:
        for field in MERGE_FILL_FIELDS:
            if field not in keep:
                continue
            if blank(keep.get(field)) and not blank(removed.get(field)):
                keep[field] = removed.get(field, "")
                changed_fields.append(field)
            elif field == "Data_Confidence" and better_confidence(keep.get(field), removed.get(field)):
                keep[field] = removed.get(field, "")
                changed_fields.append(field)

    program_ids = combine_text(*(row.get("Program_ID") for row in review_rows))
    source_urls = combine_text(*(row.get("Program_URL") for row in removed_rows))
    today = datetime.now(timezone.utc).date().isoformat()
    note = (
        f"Duplicate identity remediation {today}: merged duplicate Program_ID(s) {program_ids}; "
        f"removed duplicate URL(s) {source_urls or 'N/A'}."
    )
    keep["Notes"] = combine_text(keep.get("Notes"), note)
    return changed_fields, note


def apply_review(import_path, review_path, output_path, summary_path, write=True):
    rows = load_rows(import_path)
    review_rows = read_review_rows(review_path, import_path)
    review_by_group = defaultdict(list)
    for row in review_rows:
        review_by_group[row["Group"]].append(row)

    rows_by_id = {row["Program_ID"]: row for row in rows}
    remove_ids = set()
    log_rows = []
    for group_id, group in sorted(review_by_group.items(), key=lambda item: int(item[0])):
        keep_rows = [row for row in group if row.get("Recommendation") == "keep"]
        merge_rows = [row for row in group if row.get("Recommendation") == "merge_remove"]
        if len(keep_rows) != 1 or not merge_rows:
            continue
        keep_id = keep_rows[0]["Program_ID"]
        if keep_id not in rows_by_id:
            continue
        removed_catalog_rows = [rows_by_id[row["Program_ID"]] for row in merge_rows if row["Program_ID"] in rows_by_id]
        if not removed_catalog_rows:
            continue
        changed_fields, note = merge_into_keep(rows_by_id[keep_id], removed_catalog_rows, group)
        for removed in removed_catalog_rows:
            remove_ids.add(removed["Program_ID"])
        log_rows.append({
            "Group": group_id,
            "Recommended_Action": keep_rows[0].get("Recommended_Action", ""),
            "Keep_Program_ID": keep_id,
            "Removed_Program_IDs": "; ".join(row["Program_ID"] for row in removed_catalog_rows),
            "Changed_Fields": "; ".join(sorted(set(changed_fields))) or "Notes",
            "Note": note,
        })

    kept_rows = [row for row in rows if row["Program_ID"] not in remove_ids]
    if write and remove_ids:
        backup = output_path.parent / f"{import_path.name}.pre_duplicate_merge_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.bak"
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(import_path, backup)
        with import_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(kept_rows)
    else:
        backup = None

    if not remove_ids and output_path.exists() and summary_path.exists():
        return {
            "groups_applied": 0,
            "rows_removed": 0,
            "rows_before": len(rows),
            "rows_after": len(kept_rows),
            "backup": "",
            "output": str(output_path),
            "summary": str(summary_path),
            "log_preserved": True,
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = ["Group", "Recommended_Action", "Keep_Program_ID", "Removed_Program_IDs", "Changed_Fields", "Note"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(log_rows)

    lines = ["# Duplicate Identity Apply Log", ""]
    lines.append(f"Groups applied: {len(log_rows)}")
    lines.append(f"Rows removed: {len(remove_ids)}")
    if backup:
        lines.append(f"Backup: `{backup}`")
    lines.append("")
    for row in log_rows:
        lines.append(
            f"- Group {row['Group']}: kept {row['Keep_Program_ID']}; removed {row['Removed_Program_IDs']}; "
            f"{row['Recommended_Action']}"
        )
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "groups_applied": len(log_rows),
        "rows_removed": len(remove_ids),
        "rows_before": len(rows),
        "rows_after": len(kept_rows),
        "backup": str(backup) if backup else "",
        "output": str(output_path),
        "summary": str(summary_path),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_IMPORT)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--output", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = apply_review(args.input, args.review, args.output, args.summary, write=not args.dry_run)
    report["dry_run"] = args.dry_run
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        action = "Would remove" if args.dry_run else "Removed"
        print(f"{action} {report['rows_removed']} duplicate row(s) across {report['groups_applied']} group(s)")


if __name__ == "__main__":
    main()
