#!/usr/bin/env python3
"""Remove grant/award/funding identity rows from the reviewed public import.

Funding records can be useful local discovery leads, but the public catalog
stores student-facing opportunity programs only.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from catalog_common import ROOT, is_funding_identity_url, load_rows, text_or_none


DEFAULT_IMPORT = ROOT / "database" / "imports" / "summer_undergraduate_research_opportunities_starter.csv"
DEFAULT_OUTPUT = ROOT / "database" / "local" / "review" / "funding_identity_records_removed.csv"
DEFAULT_SUMMARY = ROOT / "database" / "local" / "review" / "funding_identity_records_removed.md"


def normalized(value):
    return text_or_none(value) or ""


def removal_reasons(row):
    reasons = []
    for field in ("Program_URL", "Application_URL", "Eligibility_Source_URL"):
        value = normalized(row.get(field))
        if value and is_funding_identity_url(value):
            reasons.append(f"{field} is a funding/award/grant identity URL")
    if normalized(row.get("Eligibility_Checked_By")).lower() == "automated_nsf_metadata":
        reasons.append("eligibility/check metadata came from automated NSF award metadata")
    if normalized(row.get("Network_Source")).lower().startswith("nsf_awards"):
        reasons.append("network source is NSF award metadata")
    return reasons


def remove_funding_identity_rows(import_path, output_path, summary_path, write=True):
    rows = load_rows(import_path)
    headers = list(rows[0]) if rows else []
    kept = []
    removed = []
    for row in rows:
        reasons = removal_reasons(row)
        if reasons:
            removed.append({
                "Program_ID": normalized(row.get("Program_ID")),
                "Program_Name": normalized(row.get("Program_Name")),
                "Host_Institution": normalized(row.get("Host_Institution")),
                "Program_URL": normalized(row.get("Program_URL")),
                "Application_URL": normalized(row.get("Application_URL")),
                "Eligibility_Source_URL": normalized(row.get("Eligibility_Source_URL")),
                "Removal_Reasons": "; ".join(reasons),
            })
        else:
            kept.append(row)

    backup = ""
    if write and removed:
        backup_path = output_path.parent / f"{import_path.name}.pre_funding_identity_cleanup_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.bak"
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(import_path, backup_path)
        with import_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
            writer.writeheader()
            writer.writerows(kept)
        backup = str(backup_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_fields = [
        "Program_ID", "Program_Name", "Host_Institution", "Program_URL",
        "Application_URL", "Eligibility_Source_URL", "Removal_Reasons",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=report_fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(removed)

    reason_counts = Counter()
    for row in removed:
        for reason in row["Removal_Reasons"].split("; "):
            reason_counts[reason] += 1
    lines = ["# Funding Identity Cleanup", ""]
    lines.append(f"Rows before: {len(rows)}")
    lines.append(f"Rows removed: {len(removed)}")
    lines.append(f"Rows kept: {len(kept)}")
    if backup:
        lines.append(f"Backup: `{backup}`")
    lines.append("")
    lines.append("Funding, award, and grant records are retained only as local discovery leads, not as public catalog opportunities.")
    lines.append("")
    lines.append("## Removal Reasons")
    for reason, count in reason_counts.most_common():
        lines.append(f"- {count}: {reason}")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "rows_before": len(rows),
        "rows_removed": len(removed),
        "rows_kept": len(kept),
        "backup": backup,
        "output": str(output_path),
        "summary": str(summary_path),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_IMPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fail-if-found", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = remove_funding_identity_rows(args.input, args.output, args.summary, write=not args.dry_run)
    report["dry_run"] = args.dry_run
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        action = "Would remove" if args.dry_run else "Removed"
        print(f"{action} {report['rows_removed']} funding identity row(s); kept {report['rows_kept']}")
    if args.fail_if_found and report["rows_removed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
