#!/usr/bin/env python3
"""Create a review queue for likely duplicate opportunity identities."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

from catalog_common import ROOT, is_funding_identity_url, load_rows, text_or_none


DEFAULT_IMPORT = ROOT / "database" / "imports" / "summer_undergraduate_research_opportunities_starter.csv"
DEFAULT_OUTPUT = ROOT / "database" / "local" / "review" / "duplicate_identity_review.csv"
DEFAULT_SUMMARY = ROOT / "database" / "local" / "review" / "duplicate_identity_review.md"

FACT_FIELDS = (
    "Duration_Weeks",
    "Program_Start",
    "Program_End",
    "Application_Open",
    "Application_Deadline",
    "Deadline_Text",
    "Stipend_Total_USD",
    "Stipend_Weekly_USD",
    "Housing_Included",
    "Meals_Included",
    "Travel_Included",
    "Academic_Credit",
    "Application_URL",
    "Raw_Eligibility_Text",
)

CONFIDENCE_SCORE = {
    "high": 30,
    "medium-high": 25,
    "medium": 20,
    "low": 5,
}


def normalized(value):
    return (text_or_none(value) or "").strip()


def normalized_identity(row):
    return (
        normalized(row.get("Host_Institution")).lower(),
        re.sub(r"\s+", " ", normalized(row.get("Program_Name")).lower()),
    )


def is_blank(value):
    value = normalized(value)
    return not value or value.upper() == "N/A"


def row_score(row):
    score = CONFIDENCE_SCORE.get(normalized(row.get("Data_Confidence")).lower(), 0)
    score += sum(1 for field in FACT_FIELDS if not is_blank(row.get(field)))
    if not is_funding_identity_url(row.get("Program_URL")):
        score += 40
    if normalized(row.get("Application_URL")) and not is_funding_identity_url(row.get("Application_URL")):
        score += 8
    try:
        score += int(row.get("Cycle_Year") or 0) / 1000
    except ValueError:
        pass
    return score


def suggested_action(group):
    return "review_same_program_multiple_pages"


def build_review_rows(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[normalized_identity(row)].append(row)

    review_rows = []
    group_number = 0
    for (_institution, _name), group in sorted(groups.items()):
        if len(group) < 2:
            continue
        group_number += 1
        keep = max(group, key=row_score)
        keep_id = normalized(keep.get("Program_ID"))
        ids = ", ".join(normalized(row.get("Program_ID")) for row in group)
        action = suggested_action(group)
        for row in sorted(group, key=lambda item: normalized(item.get("Program_ID"))):
            program_id = normalized(row.get("Program_ID"))
            review_rows.append({
                "Group": group_number,
                "Recommended_Action": action,
                "Recommendation": "keep" if program_id == keep_id else "merge_remove",
                "Keep_Program_ID": keep_id,
                "Program_ID": program_id,
                "Program_Name": normalized(row.get("Program_Name")),
                "Host_Institution": normalized(row.get("Host_Institution")),
                "Cycle_Year": normalized(row.get("Cycle_Year")),
                "Data_Confidence": normalized(row.get("Data_Confidence")),
                "Program_URL": normalized(row.get("Program_URL")),
                "Application_URL": normalized(row.get("Application_URL")),
                "Group_Program_IDs": ids,
                "Score": f"{row_score(row):.3f}",
                "Review_Note": (
                    "Likely duplicate identity. Merge rows only after official program evidence confirms "
                    "these pages describe the same continuing program."
                ),
            })
    return review_rows


def write_outputs(rows, output, summary):
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "Group", "Recommended_Action", "Recommendation", "Keep_Program_ID",
        "Program_ID", "Program_Name", "Host_Institution", "Cycle_Year",
        "Data_Confidence", "Program_URL", "Application_URL",
        "Group_Program_IDs", "Score", "Review_Note",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    groups = defaultdict(list)
    for row in rows:
        groups[row["Group"]].append(row)
    lines = ["# Duplicate Identity Review", ""]
    lines.append(f"Duplicate groups: {len(groups)}")
    lines.append(f"Rows: {len(rows)}")
    lines.append("")
    for group_id, group_rows in sorted(groups.items(), key=lambda item: int(item[0])):
        first = group_rows[0]
        remove_ids = [row["Program_ID"] for row in group_rows if row["Recommendation"] == "merge_remove"]
        lines.append(
            f"- Group {group_id}: keep {first['Keep_Program_ID']}; merge/remove {', '.join(remove_ids)}; "
            f"{first['Recommended_Action']}; {first['Program_Name']} ({first['Host_Institution']})"
        )
    summary.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_IMPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    rows = build_review_rows(load_rows(args.input))
    write_outputs(rows, args.output, args.summary)
    group_count = len({row["Group"] for row in rows})
    actions = defaultdict(int)
    for row in rows:
        if row["Recommendation"] == "keep":
            actions[row["Recommended_Action"]] += 1
    report = {
        "duplicate_groups": group_count,
        "rows": len(rows),
        "actions": dict(sorted(actions.items())),
        "output": str(args.output),
        "summary": str(args.summary),
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Duplicate identity review wrote {group_count} groups to {args.output}")


if __name__ == "__main__":
    main()
