#!/usr/bin/env python3
"""Audit NSF rows for missed optional values and enrich parseable fields."""

from __future__ import annotations

import argparse
import csv
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from automated_investigate_candidates import duration_weeks, fetch_nsf_award, stipend_amounts
from catalog_common import ROOT, load_rows, text_or_none


DEFAULT_SEED = ROOT / "database" / "imports" / "summer_undergraduate_research_opportunities_starter.csv"
DEFAULT_OUTPUT_DIR = ROOT / "database" / "local" / "review"


def is_na(value):
    return (text_or_none(value) or "").lower() in {"n/a", "na", "not applicable"}


def award_id_from_row(row):
    match = re.search(r"AWD_ID=(\d+)", row.get("Program_URL") or "")
    if match:
        return match.group(1)
    match = re.match(r"NSF-REU-(\d+)$", row.get("Program_ID") or "")
    return match.group(1) if match else None


def maybe_int_string(value):
    if value is None:
        return None
    return str(int(value)) if float(value).is_integer() else str(value)


def existing_number(value):
    value = text_or_none(value)
    if not value or is_na(value):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def audit_and_update(seed_path, output_dir, delay=0.02):
    rows = load_rows(seed_path)
    headers = list(rows[0])
    audit_rows = []
    updated = 0
    confirmed = 0
    reviewed = 0
    for row in rows:
        if not (row.get("Program_ID") or "").startswith("NSF-REU-"):
            continue
        missing = [
            field for field in ("Duration_Weeks", "Stipend_Total_USD", "Stipend_Weekly_USD")
            if is_na(row.get(field)) or not text_or_none(row.get(field))
        ]
        existing = [
            field for field in ("Duration_Weeks", "Stipend_Total_USD", "Stipend_Weekly_USD")
            if field not in missing and text_or_none(row.get(field))
        ]
        if not missing and not existing:
            continue
        reviewed += 1
        award_id = award_id_from_row(row)
        if not award_id:
            audit_rows.append({**base_audit_row(row), "Fields_Checked": "; ".join(missing), "Outcome": "award id unavailable"})
            continue
        try:
            award = fetch_nsf_award(award_id)
        except Exception as error:  # noqa: BLE001 - audit should continue.
            audit_rows.append({**base_audit_row(row), "Fields_Checked": "; ".join(missing), "Outcome": f"fetch failed: {type(error).__name__}"})
            continue
        abstract = award.get("abstractText") or ""
        found = []
        parser_confirmed = []
        duration = duration_weeks(abstract)
        stipend_total, stipend_weekly = stipend_amounts(abstract)
        if "Duration_Weeks" in missing and duration:
            row["Duration_Weeks"] = str(duration)
            found.append(f"Duration_Weeks={duration}")
        elif duration and existing_number(row.get("Duration_Weeks")) == float(duration):
            parser_confirmed.append(f"Duration_Weeks={duration}")
        if "Stipend_Total_USD" in missing and stipend_total:
            row["Stipend_Total_USD"] = maybe_int_string(stipend_total)
            found.append(f"Stipend_Total_USD={maybe_int_string(stipend_total)}")
        elif stipend_total and existing_number(row.get("Stipend_Total_USD")) == stipend_total:
            parser_confirmed.append(f"Stipend_Total_USD={maybe_int_string(stipend_total)}")
        if "Stipend_Weekly_USD" in missing and stipend_weekly:
            row["Stipend_Weekly_USD"] = maybe_int_string(stipend_weekly)
            found.append(f"Stipend_Weekly_USD={maybe_int_string(stipend_weekly)}")
        elif stipend_weekly and existing_number(row.get("Stipend_Weekly_USD")) == stipend_weekly:
            parser_confirmed.append(f"Stipend_Weekly_USD={maybe_int_string(stipend_weekly)}")
        if found:
            updated += 1
            outcome = "updated: " + "; ".join(found)
        elif parser_confirmed:
            confirmed += 1
            outcome = "confirmed parser handled existing value: " + "; ".join(parser_confirmed)
        else:
            outcome = "no parseable duration/stipend value found in official NSF abstract"
        audit_rows.append({**base_audit_row(row), "Fields_Checked": "; ".join(missing), "Outcome": outcome})
        if delay:
            time.sleep(delay)

    with seed_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    csv_path, md_path = write_audit(audit_rows, output_dir)
    return {"reviewed": reviewed, "updated": updated, "confirmed": confirmed, "audit_csv": csv_path, "audit_md": md_path}


def base_audit_row(row):
    return {
        "Program_ID": row.get("Program_ID") or "",
        "Program_Name": row.get("Program_Name") or "",
        "Host_Institution": row.get("Host_Institution") or "",
        "Cycle_Year": row.get("Cycle_Year") or "",
        "Program_URL": row.get("Program_URL") or "",
    }


def write_audit(rows, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "nsf_optional_field_detection_audit.csv"
    md_path = output_dir / "nsf_optional_field_detection_audit.md"
    headers = [
        "Program_ID",
        "Program_Name",
        "Host_Institution",
        "Cycle_Year",
        "Program_URL",
        "Fields_Checked",
        "Outcome",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    updated = [row for row in rows if row["Outcome"].startswith("updated:")]
    confirmed = [row for row in rows if row["Outcome"].startswith("confirmed parser handled")]
    lines = [
        "# NSF optional field detection audit",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- NSF opportunities checked: {len(rows)}",
        f"- Opportunities enriched from alternate formatting: {len(updated)}",
        f"- Opportunities with parser-confirmed existing values: {len(confirmed)}",
        "",
    ]
    for row in rows:
        lines.append(
            f"- {row['Program_ID']} | {row['Host_Institution']} | {row['Fields_Checked']}: "
            f"{row['Outcome']} | {row['Program_URL']}"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path, md_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--delay", type=float, default=0.02)
    args = parser.parse_args()
    result = audit_and_update(args.seed, args.output_dir, args.delay)
    print(f"NSF optional field audit checked {result['reviewed']} opportunity row(s).")
    print(f"Enriched {result['updated']} row(s) from alternate formatting.")
    print(f"Confirmed parser-handled values in {result['confirmed']} row(s).")
    print(f"Audit CSV: {result['audit_csv']}")
    print(f"Audit summary: {result['audit_md']}")


if __name__ == "__main__":
    main()
