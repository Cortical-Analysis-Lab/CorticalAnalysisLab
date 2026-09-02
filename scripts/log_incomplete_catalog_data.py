#!/usr/bin/env python3
"""Write a local review log for catalog rows with visible N/A placeholders."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

from catalog_common import ROOT, load_rows, text_or_none


DEFAULT_SEED = ROOT / "database" / "imports" / "summer_undergraduate_research_opportunities_starter.csv"
DEFAULT_OUTPUT_DIR = ROOT / "database" / "local" / "review"
FIELDS_TO_REVIEW = [
    "Duration_Weeks",
    "Program_Start",
    "Program_End",
    "Application_Open",
    "Application_Deadline",
    "Deadline_Text",
    "Stipend_Total_USD",
    "Stipend_Weekly_USD",
]


def is_na(value):
    return (text_or_none(value) or "").lower() in {"n/a", "na", "not applicable"}


def build_log_rows(seed_path):
    log_rows = []
    for row in load_rows(seed_path):
        fields = [field for field in FIELDS_TO_REVIEW if is_na(row.get(field))]
        if not fields:
            continue
        reasons = []
        if any(field in fields for field in ("Program_Start", "Program_End", "Application_Open", "Application_Deadline", "Deadline_Text")):
            reasons.append("official source did not provide cycle date/deadline fields")
        if "Duration_Weeks" in fields:
            reasons.append("duration was not found after numeric, hyphenated, and word-number week parsing")
        if any(field in fields for field in ("Stipend_Total_USD", "Stipend_Weekly_USD")):
            reasons.append("stipend amount was not found near stipend/support wording")
        log_rows.append({
            "Program_ID": row.get("Program_ID") or "",
            "Program_Name": row.get("Program_Name") or "",
            "Host_Institution": row.get("Host_Institution") or "",
            "Cycle_Year": row.get("Cycle_Year") or "",
            "Fields_Recorded_As_NA": "; ".join(fields),
            "Program_URL": row.get("Program_URL") or "",
            "Application_URL": row.get("Application_URL") or "",
            "Last_Verified": row.get("Last_Verified") or "",
            "Reason": "; ".join(reasons),
        })
    return log_rows


def write_logs(rows, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "incomplete_data_review_log.csv"
    md_path = output_dir / "incomplete_data_review_log.md"
    headers = [
        "Program_ID",
        "Program_Name",
        "Host_Institution",
        "Cycle_Year",
        "Fields_Recorded_As_NA",
        "Program_URL",
        "Application_URL",
        "Last_Verified",
        "Reason",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# Incomplete data review log",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Opportunities needing optional data review: {len(rows)}",
        "",
    ]
    for row in rows:
        lines.append(
            f"- {row['Program_ID']} | {row['Host_Institution']} | {row['Program_Name']} "
            f"({row['Cycle_Year']}): {row['Fields_Recorded_As_NA']} | {row['Program_URL']}"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path, md_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    rows = build_log_rows(args.seed)
    csv_path, md_path = write_logs(rows, args.output_dir)
    print(f"Incomplete data review log: {csv_path}")
    print(f"Incomplete data review summary: {md_path}")
    print(f"Rows: {len(rows)}")


if __name__ == "__main__":
    main()
